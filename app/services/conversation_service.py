from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Generator, Dict, Any
from app.services.langgraph_service import LangGraphService
from app.core.models import Message, DigitalHuman, ConversationCheckpoint
from app.schemas.conversation import *
import json
from datetime import datetime
from sqlalchemy import desc, and_


class ConversationService:

    def __init__(self, db: Session, langgraph_service: LangGraphService):
        self.db = db
        self.langgraph_service = langgraph_service
    
    def create_conversation(
        self,
        conversation_data: ConversationCreate,
        user_id: int
    ) -> Dict[str, Any]:
        # 使用固定格式的 thread_id：chat_{digital_human_id}_{user_id}
        # 这样同一个用户与同一个数字人只会有一个持续对话
        thread_id = f"chat_{conversation_data.digital_human_id}_{user_id}"

        # 检查是否已经存在该对话
        existing = self.get_conversation_by_thread_id(thread_id, user_id)
        if existing:
            # 如果已存在，直接返回现有对话
            return existing

        # 创建初始 checkpoint 记录会话元信息
        checkpoint = ConversationCheckpoint(
            thread_id=thread_id,
            user_id=user_id,
            digital_human_id=conversation_data.digital_human_id,
            version=0,
            checkpoint_data={},
            channel_values={"messages": []},
            checkpoint_metadata={
                "title": conversation_data.title or "新对话",
                "created_at": datetime.now().isoformat()
            }
        )
        self.db.add(checkpoint)
        self.db.commit()

        return {
            "user_id": user_id,
            "digital_human_id": conversation_data.digital_human_id,
            "title": conversation_data.title or "新对话",
            "created_at": checkpoint.created_at,
            "last_message_at": None
        }

    def get_or_create_conversation(
        self,
        digital_human_id: int,
        user_id: int,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取或创建对话
        使用固定格式的 thread_id，确保用户与数字人之间只有一个持续对话
        """
        # 使用固定格式的 thread_id
        thread_id = f"chat_{digital_human_id}_{user_id}"

        # 尝试获取现有对话
        existing = self.get_conversation_by_thread_id(thread_id, user_id)
        if existing:
            # 如果提供了新标题，更新标题
            if title and title != existing.get("title"):
                self.update_conversation(
                    thread_id,
                    ConversationUpdate(title=title),
                    user_id
                )
                existing["title"] = title
            return existing

        # 如果不存在，创建新对话
        conversation_data = ConversationCreate(
            digital_human_id=digital_human_id,
            title=title
        )
        return self.create_conversation(conversation_data, user_id)

    def get_conversation_by_thread_id(
        self,
        thread_id: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        checkpoint = self.db.query(ConversationCheckpoint).filter(
            and_(
                ConversationCheckpoint.thread_id == thread_id,
                ConversationCheckpoint.user_id == user_id
            )
        ).order_by(desc(ConversationCheckpoint.version)).first()

        if not checkpoint:
            return None

        metadata = checkpoint.checkpoint_metadata or {}
        return {
            "user_id": checkpoint.user_id,
            "digital_human_id": checkpoint.digital_human_id,
            "title": metadata.get("title", "对话"),
            "created_at": checkpoint.created_at,
            "last_message_at": metadata.get("last_message_at")
        }
    
    def get_conversations_paginated(
        self,
        page_request: ConversationPageRequest,
        user_id: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        # 获取用户的所有 thread_id（通过 checkpoint 表）
        query = self.db.query(
            ConversationCheckpoint.thread_id,
            ConversationCheckpoint.user_id,
            ConversationCheckpoint.digital_human_id,
            ConversationCheckpoint.checkpoint_metadata,
            ConversationCheckpoint.created_at
        ).filter(
            ConversationCheckpoint.user_id == user_id
        ).distinct(
            ConversationCheckpoint.thread_id
        )

        # 分页
        total = query.count()
        offset = (page_request.page - 1) * page_request.size
        items = query.limit(page_request.size).offset(offset).all()

        conversations = []
        for item in items:
            metadata = item.checkpoint_metadata or {}
            conversations.append({
                "user_id": item.user_id,
                "digital_human_id": item.digital_human_id,
                "title": metadata.get("title", "对话"),
                "created_at": item.created_at,
                "last_message_at": metadata.get("last_message_at")
            })

        return conversations, total
    
    def update_conversation(
        self,
        thread_id: str,
        conversation_data: ConversationUpdate,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        checkpoint = self.db.query(ConversationCheckpoint).filter(
            and_(
                ConversationCheckpoint.thread_id == thread_id,
                ConversationCheckpoint.user_id == user_id
            )
        ).order_by(desc(ConversationCheckpoint.version)).first()

        if not checkpoint:
            return None

        # 更新元数据
        metadata = checkpoint.checkpoint_metadata or {}
        if conversation_data.title:
            metadata["title"] = conversation_data.title
        checkpoint.checkpoint_metadata = metadata
        self.db.commit()

        return {
            "user_id": checkpoint.user_id,
            "digital_human_id": checkpoint.digital_human_id,
            "title": metadata.get("title", "对话"),
            "created_at": checkpoint.created_at
        }
    
    def delete_conversation(self, thread_id: str, user_id: int) -> bool:
        # 删除所有相关的 checkpoint 和消息
        self.db.query(ConversationCheckpoint).filter(
            and_(
                ConversationCheckpoint.thread_id == thread_id,
                ConversationCheckpoint.user_id == user_id
            )
        ).delete()

        self.db.query(Message).filter(
            and_(
                Message.thread_id == thread_id,
                Message.user_id == user_id
            )
        ).delete()

        self.db.commit()
        return True
    
    def get_conversation_with_messages(
        self,
        thread_id: str,
        user_id: int,
        message_limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        # 获取会话信息
        conversation = self.get_conversation_by_thread_id(thread_id, user_id)
        if not conversation:
            return None

        # 获取消息
        query = self.db.query(Message).filter(
            and_(
                Message.user_id == user_id,
                Message.digital_human_id == conversation["digital_human_id"]
            )
        ).order_by(Message.created_at)

        if message_limit:
            query = query.limit(message_limit)

        messages = query.all()

        return {
            **conversation,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "tokens_used": msg.tokens_used,
                    "metadata": msg.message_metadata,
                    "memory": msg.memory,
                    "created_at": msg.created_at
                } for msg in messages
            ]
        }
    
    def send_message(
        self,
        thread_id: str,
        message_content: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        # 获取会话信息
        conversation = self.get_conversation_by_thread_id(thread_id, user_id)
        if not conversation:
            return None

        # 保存用户消息
        user_message = Message(
            user_id=user_id,
            digital_human_id=conversation["digital_human_id"],
            role="user",
            content=message_content,
            message_metadata={
                "input_tokens": len(message_content.split()),
                "input_length": len(message_content),
                "timestamp": datetime.now().isoformat()
            }
        )
        self.db.add(user_message)
        self.db.commit()

        # 获取数字人配置
        digital_human_config = self._get_digital_human_config(
            conversation["digital_human_id"]
        )

        try:
            # 记录开始时间
            start_time = datetime.now()

            # 调用 AI 生成响应
            result = self.langgraph_service.chat_sync(
                message_content,
                thread_id,
                digital_human_config
            )
            ai_response = result["response"]
            memory_data = result.get("memory")

            # 计算元信息
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 更新元信息，包含记忆信息
            metadata = {
                "response_time_ms": response_time_ms,
                "response_tokens": len(ai_response.split()),
                "response_length": len(ai_response),
                "model": digital_human_config.get("model", "gpt-4o-mini"),
                "temperature": digital_human_config.get("temperature", 0.7),
                "sync_mode": True,
                "timestamp": datetime.now().isoformat()
            }

            # 如果有记忆，添加到元信息中
            if memory_data:
                metadata["has_memory"] = True
                metadata["memory_count"] = memory_data.get("metadata", {}).get("count", 0)

            # 保存 AI 消息和元信息
            ai_message = Message(
                user_id=user_id,
                digital_human_id=conversation["digital_human_id"],
                role="assistant",
                content=ai_response,
                message_metadata=metadata,
                memory=memory_data,  # 新增：保存记忆搜索数据
                tokens_used=len(ai_response.split())
            )
            self.db.add(ai_message)
            self.db.commit()

            return {
                "id": ai_message.id,
                "role": "assistant",
                "content": ai_response,
                "tokens_used": ai_message.tokens_used,
                "metadata": ai_message.message_metadata,
                "memory": ai_message.memory,  # 新增：返回记忆信息
                "created_at": ai_message.created_at
            }

        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(f"消息发送失败: {str(e)}")
    
    def send_message_stream(
        self,
        thread_id: str,
        message_content: str,
        user_id: int
    ) -> Generator[str, None, None]:
        # 获取会话信息
        conversation = self.get_conversation_by_thread_id(thread_id, user_id)
        if not conversation:
            yield json.dumps({
                "type": "error",
                "content": "对话不存在或无权限访问"
            })
            return

        # 保存用户消息
        try:
            user_message = Message(
                user_id=user_id,
                digital_human_id=conversation["digital_human_id"],
                role="user",
                content=message_content,
                message_metadata={
                    "input_tokens": len(message_content.split()),
                    "input_length": len(message_content),
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.db.add(user_message)
            self.db.commit()
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "content": f"保存消息失败: {str(e)}"
            })
            return

        yield json.dumps({
            "type": "message",
            "content": "",
            "metadata": {
                "message_id": user_message.id,
                "role": "user",
                "content": message_content
            }
        })

        # 获取数字人配置
        digital_human_config = self._get_digital_human_config(
            conversation["digital_human_id"]
        )

        # 初始化元信息收集
        metadata = {
            "has_memory": False,
            "memory_count": 0,
            "response_tokens": 0,
            "stream_chunks": 0,
            "start_time": datetime.now().isoformat(),
            "model": digital_human_config.get("model", "gpt-4o-mini"),
            "temperature": digital_human_config.get("temperature", 0.7),
            "max_tokens": digital_human_config.get("max_tokens", 2048)
        }
        start_time = datetime.now()
        memory_data = None  # 新增：存储记忆搜索数据

        full_response = ""
        try:
            for chunk in self.langgraph_service.chat_stream(
                message_content,
                thread_id,
                digital_human_config
            ):
                # 检查 chunk 是否是 JSON 格式的状态消息
                try:
                    # 尝试解析为 JSON
                    data = json.loads(chunk)
                    # 收集元信息
                    if data.get("type") == "memory":
                        metadata["has_memory"] = True
                        metadata["memory_count"] = data.get("metadata", {}).get("count", 0)
                        memory_data = data  # 保存完整的记忆搜索数据
                    # 直接转发给前端，但不追加到 full_response
                    yield chunk
                except (json.JSONDecodeError, TypeError):
                    # 不是 JSON，是实际的 AI 回复内容
                    # 统计信息
                    metadata["stream_chunks"] += 1
                    metadata["response_tokens"] += len(chunk.split())
                    # 追加到 full_response 并发送给前端
                    full_response += chunk
                    yield json.dumps({
                        "type": "token",
                        "content": chunk
                    })
        except ValueError as e:
            yield json.dumps({
                "type": "error",
                "content": str(e)
            })
            return
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "content": f"AI响应生成失败: {str(e)}"
            })
            return

        # 计算最终的元信息
        metadata["end_time"] = datetime.now().isoformat()
        metadata["response_time_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
        metadata["response_length"] = len(full_response)

        # 保存 AI 消息
        try:
            ai_message = Message(
                user_id=user_id,
                digital_human_id=conversation["digital_human_id"],
                role="assistant",
                content=full_response,
                message_metadata=metadata,
                memory=memory_data,  # 新增：保存记忆搜索数据
                tokens_used=metadata["response_tokens"]
            )
            self.db.add(ai_message)
            self.db.commit()
        except Exception as e:
            print(f"Warning: Failed to save AI message: {str(e)}")
            ai_message = None

        # 发送完成消息，包含统计信息
        yield json.dumps({
            "type": "done",
            "content": "",
            "metadata": {
                "message_id": ai_message.id if ai_message else None,
                "tokens_used": metadata["response_tokens"],
                "response_time_ms": metadata["response_time_ms"],
                "has_memory": metadata["has_memory"],
                "memory_count": metadata["memory_count"],
                "stream_chunks": metadata["stream_chunks"],
                "response_length": metadata["response_length"]
            }
        })
    
    def _get_digital_human_config(self, digital_human_id: int) -> Dict[str, Any]:
        digital_human = self.db.query(DigitalHuman).filter(
            DigitalHuman.id == digital_human_id
        ).first()

        if not digital_human:
            return {}

        return {
            "id": digital_human.id,  # 新增：传递ID用于记忆搜索
            "name": digital_human.name,
            "type": digital_human.type,
            "skills": digital_human.skills or [],
            "personality": digital_human.personality or {},
            "conversation_style": digital_human.conversation_style,
            "temperature": digital_human.temperature,
            "max_tokens": digital_human.max_tokens,
            "system_prompt": digital_human.system_prompt
        }
    
    def get_conversation_messages(
        self,
        thread_id: str,
        user_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        # 从 thread_id 解析出 digital_human_id
        parts = thread_id.split('_')
        if len(parts) >= 3 and parts[0] == 'chat':
            digital_human_id = int(parts[1])
        else:
            return []

        query = self.db.query(Message).filter(
            and_(
                Message.user_id == user_id,
                Message.digital_human_id == digital_human_id
            )
        ).order_by(Message.created_at)

        if limit:
            query = query.limit(limit)

        messages = query.all()

        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "tokens_used": msg.tokens_used,
                "metadata": msg.message_metadata,
                "created_at": msg.created_at
            } for msg in messages
        ]
    
    def clear_conversation_history(
        self,
        thread_id: str,
        user_id: int
    ) -> bool:
        # 从 thread_id 解析出 digital_human_id
        parts = thread_id.split('_')
        if len(parts) >= 3 and parts[0] == 'chat':
            digital_human_id = int(parts[1])
        else:
            return False

        # 删除所有消息
        self.db.query(Message).filter(
            and_(
                Message.user_id == user_id,
                Message.digital_human_id == digital_human_id
            )
        ).delete()
        self.db.commit()

        # 清空 LangGraph 中的对话历史
        self.langgraph_service.clear_conversation(thread_id)

        return True