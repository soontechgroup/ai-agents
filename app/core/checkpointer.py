from typing import Any, Dict, Optional, Iterator, List, Tuple, AsyncIterator
from datetime import datetime, timedelta
import json
import hashlib
import asyncio
from collections import OrderedDict
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from langchain_core.messages import BaseMessage
from app.core.messages import UserMessage, AssistantMessage, SystemMessage, deserialize_message, serialize_message, is_message_dict
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from app.core.models import Conversation, Message, ConversationCheckpoint
from app.core.logger import logger
import threading
from functools import lru_cache


class MySQLCheckpointer(BaseCheckpointSaver):

    def __init__(self, db_session_factory, cache_size: int = 100, cache_ttl: int = 300):
        super().__init__()
        self.db_session_factory = db_session_factory
        self.cache_ttl = cache_ttl
        self._cache = OrderedDict()
        self._cache_timestamps = {}
        self._lock = threading.RLock()

        self._get_conversation_cached = lru_cache(maxsize=cache_size)(self._get_conversation)

    def _get_conversation(self, thread_id: str) -> Optional[Conversation]:
        db_gen = self.db_session_factory()
        db = next(db_gen)
        return db.query(Conversation).filter(Conversation.thread_id == thread_id).first()

    def _serialize_messages(self, messages: List[Any]) -> List[Dict]:
        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                serialized.append(msg)
            elif isinstance(msg, BaseMessage):
                serialized.append(serialize_message(msg))
            else:
                logger.warning(f"Unknown message type in serialization: {type(msg)}")
        return serialized

    def _deep_serialize_messages(self, obj: Any) -> Any:
        if isinstance(obj, BaseMessage):
            return serialize_message(obj)
        elif isinstance(obj, dict):
            return {k: self._deep_serialize_messages(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_serialize_messages(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._deep_serialize_messages(item) for item in obj)
        else:
            return obj

    def _deep_deserialize_messages(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            # 尝试反序列化为消息
            if is_message_dict(obj):
                msg = deserialize_message(obj)
                if msg is not None:
                    return msg
            
            # 不是消息格式，递归处理子元素
            return {k: self._deep_deserialize_messages(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_deserialize_messages(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._deep_deserialize_messages(item) for item in obj)
        else:
            return obj

    def _deserialize_messages(self, serialized: List[Dict]) -> List[BaseMessage]:
        messages = []
        for msg_data in serialized:
            msg = deserialize_message(msg_data)
            if msg is not None:
                messages.append(msg)
            else:
                logger.warning(f"Failed to deserialize message: {msg_data}")
        return messages

    def _get_cache_key(self, thread_id: str, version: Optional[int] = None) -> str:
        if version is None:
            return f"thread:{thread_id}:latest"
        return f"thread:{thread_id}:v{version}"

    def _get_from_cache(self, thread_id: str, version: Optional[int] = None) -> Optional[Checkpoint]:
        with self._lock:
            cache_key = self._get_cache_key(thread_id, version)

            if cache_key in self._cache:
                timestamp = self._cache_timestamps.get(cache_key)
                if timestamp and (datetime.now() - timestamp).seconds < self.cache_ttl:
                    self._cache.move_to_end(cache_key)
                    return self._cache[cache_key]
                else:
                    del self._cache[cache_key]
                    del self._cache_timestamps[cache_key]

            return None

    def _put_to_cache(self, thread_id: str, checkpoint: Checkpoint, version: Optional[int] = None):
        with self._lock:
            cache_key = self._get_cache_key(thread_id, version)

            if len(self._cache) >= 100:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                if oldest_key in self._cache_timestamps:
                    del self._cache_timestamps[oldest_key]

            self._cache[cache_key] = checkpoint
            self._cache_timestamps[cache_key] = datetime.now()

    def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        thread_id = config.get("configurable", {}).get("thread_id")
        version = config.get("configurable", {}).get("version")

        if not thread_id:
            return None

        cached_checkpoint = self._get_from_cache(thread_id, version)
        if cached_checkpoint:
            logger.debug(f"从缓存获取检查点: thread_id={thread_id}, version={version}")
            return cached_checkpoint

        db_gen = self.db_session_factory()
        db = next(db_gen)
        try:
            if version is not None:
                checkpoint_record = db.query(ConversationCheckpoint).filter(
                    and_(
                        ConversationCheckpoint.thread_id == thread_id,
                        ConversationCheckpoint.version == version
                    )
                ).first()

                if checkpoint_record:
                    checkpoint = self._deep_deserialize_messages(checkpoint_record.checkpoint_data)
                    self._put_to_cache(thread_id, checkpoint, version)
                    return checkpoint

                return None

            latest_checkpoint = db.query(ConversationCheckpoint).filter(
                ConversationCheckpoint.thread_id == thread_id
            ).order_by(desc(ConversationCheckpoint.version)).first()

            if latest_checkpoint:
                checkpoint = self._deep_deserialize_messages(latest_checkpoint.checkpoint_data)
                self._put_to_cache(thread_id, checkpoint)
                return checkpoint

            conversation = db.query(Conversation).filter(
                Conversation.thread_id == thread_id
            ).first()

            if not conversation:
                return None

            messages = db.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at).limit(50).all()

            langchain_messages = []
            for msg in messages:
                if msg.role == "user":
                    langchain_messages.append(UserMessage(content=msg.content))
                elif msg.role == "assistant":
                    langchain_messages.append(AssistantMessage(content=msg.content))
                elif msg.role == "system":
                    langchain_messages.append(SystemMessage(content=msg.content))

            checkpoint = {
                "v": 1,
                "ts": conversation.updated_at.isoformat() if conversation.updated_at else datetime.now().isoformat(),
                "channel_values": {
                    "messages": langchain_messages
                },
                "channel_versions": {
                    "messages": len(messages)
                },
                "versions_seen": {}
            }

            self._put_to_cache(thread_id, checkpoint)

            return checkpoint
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata,
            new_versions: Dict[str, int]) -> Dict[str, Any]:
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id or not checkpoint:
            return config

        db_gen = self.db_session_factory()
        db = next(db_gen)
        try:
            try:
                conversation = db.query(Conversation).filter(
                    Conversation.thread_id == thread_id
                ).first()

                conversation_id = conversation.id if conversation else None

                max_version = db.query(ConversationCheckpoint.version).filter(
                    ConversationCheckpoint.thread_id == thread_id
                ).order_by(desc(ConversationCheckpoint.version)).first()

                new_version = (max_version[0] + 1) if max_version else 1

                serialized_checkpoint = self._deep_serialize_messages(checkpoint)

                channel_values = serialized_checkpoint.get("channel_values", {})
                serialized_metadata = self._deep_serialize_messages(metadata) if metadata else {}

                checkpoint_record = ConversationCheckpoint(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    version=new_version,
                    parent_version=new_version - 1 if new_version > 1 else None,
                    checkpoint_data=serialized_checkpoint,
                    channel_values=channel_values,
                    channel_versions=serialized_checkpoint.get("channel_versions", {}),
                    checkpoint_metadata=serialized_metadata
                )

                db.add(checkpoint_record)

                if conversation and "messages" in channel_values:
                    serialized_messages = channel_values["messages"]
                    if serialized_messages:
                        last_msg_data = serialized_messages[-1]

                        existing = db.query(Message).filter(
                            and_(
                                Message.conversation_id == conversation.id,
                                Message.content == last_msg_data.get("content", "")
                            )
                        ).first()

                        if not existing:
                            role = last_msg_data.get("role", "user")

                            new_message = Message(
                                conversation_id=conversation.id,
                                role=role,
                                content=last_msg_data.get("content", ""),
                                message_metadata=last_msg_data.get("additional_kwargs", {})
                            )
                            db.add(new_message)

                    conversation.last_message_at = datetime.now()

                db.commit()

                with self._lock:
                    keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"thread:{thread_id}:")]
                    for key in keys_to_delete:
                        del self._cache[key]
                        if key in self._cache_timestamps:
                            del self._cache_timestamps[key]

                logger.info(f"保存检查点成功: thread_id={thread_id}, version={new_version}")

                updated_config = dict(config)
                updated_config.setdefault("configurable", {})["version"] = new_version
                return updated_config

            except Exception as e:
                db.rollback()
                logger.error(f"保存检查点失败: {e}")
                raise
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def list(
            self,
            config: Optional[Dict[str, Any]] = None,
            *,
            before: Optional[Dict[str, Any]] = None,
            limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        db_gen = self.db_session_factory()
        db = next(db_gen)
        try:
            query = db.query(ConversationCheckpoint)

            if config and "configurable" in config:
                thread_id = config["configurable"].get("thread_id")
                if thread_id:
                    query = query.filter(ConversationCheckpoint.thread_id == thread_id)

            if before:
                before_time = before.get("ts")
                if before_time:
                    query = query.filter(ConversationCheckpoint.created_at < before_time)

            query = query.order_by(desc(ConversationCheckpoint.created_at))

            if limit:
                query = query.limit(limit)

            for checkpoint_record in query:
                checkpoint_data = dict(checkpoint_record.checkpoint_data)
                if "channel_values" in checkpoint_data and "messages" in checkpoint_data["channel_values"]:
                    serialized_messages = checkpoint_data["channel_values"]["messages"]
                    checkpoint_data["channel_values"]["messages"] = self._deserialize_messages(serialized_messages)

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": checkpoint_record.thread_id,
                            "version": checkpoint_record.version
                        }
                    },
                    checkpoint=checkpoint_data,
                    metadata={
                        "version": checkpoint_record.version,
                        "parent_version": checkpoint_record.parent_version,
                        "created_at": checkpoint_record.created_at.isoformat(),
                        **(checkpoint_record.checkpoint_metadata or {})
                    }
                )
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        checkpoint = self.get(config)
        if not checkpoint:
            return None

        thread_id = config.get("configurable", {}).get("thread_id")
        version = config.get("configurable", {}).get("version")

        db_gen = self.db_session_factory()
        db = next(db_gen)
        try:
            if version:
                checkpoint_record = db.query(ConversationCheckpoint).filter(
                    and_(
                        ConversationCheckpoint.thread_id == thread_id,
                        ConversationCheckpoint.version == version
                    )
                ).first()
            else:
                checkpoint_record = db.query(ConversationCheckpoint).filter(
                    ConversationCheckpoint.thread_id == thread_id
                ).order_by(desc(ConversationCheckpoint.version)).first()

            if checkpoint_record:
                metadata = {
                    "version": checkpoint_record.version,
                    "parent_version": checkpoint_record.parent_version,
                    "created_at": checkpoint_record.created_at.isoformat(),
                    **(checkpoint_record.checkpoint_metadata or {})
                }
            else:
                metadata = None
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata
        )

    def put_writes(self, config: Dict[str, Any], writes: list, task_id: str) -> None:
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return

        db_gen = self.db_session_factory()
        db = next(db_gen)
        try:
            metadata = {
                "task_id": task_id,
                "writes": writes,
                "timestamp": datetime.now().isoformat()
            }

            self.put(config, {"writes": writes}, metadata, {})
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def clear_cache(self, thread_id: Optional[str] = None):
        with self._lock:
            if thread_id:
                keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"thread:{thread_id}:")]
                for key in keys_to_delete:
                    del self._cache[key]
                    if key in self._cache_timestamps:
                        del self._cache_timestamps[key]
            else:
                self._cache.clear()
                self._cache_timestamps.clear()

    def get_version_history(self, thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        db_gen = self.db_session_factory()
        db = next(db_gen)
        try:
            checkpoints = db.query(ConversationCheckpoint).filter(
                ConversationCheckpoint.thread_id == thread_id
            ).order_by(desc(ConversationCheckpoint.version)).limit(limit).all()

            history = []
            for cp in checkpoints:
                history.append({
                    "version": cp.version,
                    "parent_version": cp.parent_version,
                    "created_at": cp.created_at.isoformat(),
                    "metadata": cp.checkpoint_metadata
                })

            return history
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def rollback_to_version(self, thread_id: str, version: int) -> bool:
        config = {"configurable": {"thread_id": thread_id, "version": version}}
        checkpoint = self.get(config)

        if checkpoint:
            new_config = {"configurable": {"thread_id": thread_id}}
            self.put(new_config, checkpoint, {"rollback_from": version}, {})
            return True

        return False

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self.get_tuple, config
        )

    async def aget(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        checkpoint_tuple = await self.aget_tuple(config)
        if checkpoint_tuple:
            return checkpoint_tuple.checkpoint
        return None

    async def aput(self, config: Dict[str, Any], checkpoint: Checkpoint,
                   metadata: Optional[CheckpointMetadata] = None,
                   new_versions: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self.put, config, checkpoint, metadata, new_versions
        )

    async def aput_writes(self, config: Dict[str, Any], writes: list, task_id: str) -> None:
        return await asyncio.get_running_loop().run_in_executor(
            None, self.put_writes, config, writes, task_id
        )

    async def alist(self, config: Optional[Dict[str, Any]] = None, *,
                    before: Optional[Dict[str, Any]] = None,
                    limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        results = await asyncio.get_running_loop().run_in_executor(
            None, lambda: list(self.list(config, before=before, limit=limit))
        )
        for item in results:
            yield item
