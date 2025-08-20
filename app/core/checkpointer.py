"""
PostgreSQL Checkpointer for LangGraph
实现基于 PostgreSQL 的 checkpointer，避免双层缓存
"""
from typing import Any, Dict, Optional, Iterator
from datetime import datetime
import json
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from app.core.models import Conversation, Message


class PostgresCheckpointer(BaseCheckpointSaver):
    """基于 PostgreSQL 的 LangGraph Checkpointer"""
    
    def __init__(self, db_session_factory):
        """
        初始化 PostgreSQL Checkpointer
        
        Args:
            db_session_factory: 数据库会话工厂函数
        """
        super().__init__()
        self.db_session_factory = db_session_factory
    
    def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """
        获取指定配置的检查点
        
        Args:
            config: 包含 thread_id 的配置字典
            
        Returns:
            检查点数据或 None
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None
        
        with self.db_session_factory() as db:
            # 通过 thread_id 查找对话
            conversation = db.query(Conversation).filter(
                Conversation.thread_id == thread_id
            ).first()
            
            if not conversation:
                return None
            
            # 获取最近的消息（限制数量避免内存过大）
            messages = db.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at.desc()).limit(20).all()
            
            # 反转顺序，让消息按时间正序
            messages.reverse()
            
            # 转换为 LangChain 消息对象
            langchain_messages = []
            for msg in messages:
                if msg.role == "user":
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    langchain_messages.append(AIMessage(content=msg.content))
                elif msg.role == "system":
                    langchain_messages.append(SystemMessage(content=msg.content))
            
            # 构建检查点
            checkpoint = {
                "v": 1,
                "ts": conversation.updated_at.isoformat() if conversation.updated_at else datetime.now().isoformat(),
                "channel_values": {
                    "messages": langchain_messages
                },
                "channel_versions": {},
                "versions_seen": {}
            }
            
            return checkpoint
    
    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: Optional[CheckpointMetadata] = None) -> Dict[str, Any]:
        """
        保存检查点（这里我们不需要额外保存，因为消息已经在数据库中）
        
        Args:
            config: 配置字典
            checkpoint: 检查点数据
            metadata: 元数据
            
        Returns:
            配置字典
        """
        # 由于我们直接使用数据库中的消息，不需要额外保存
        # 消息已经通过 conversation_service 保存到数据库
        return config
    
    def put_writes(self, config: Dict[str, Any], writes: list, task_id: str) -> None:
        """
        保存写入操作（可选实现）
        """
        pass
    
    def list(self, config: Optional[Dict[str, Any]] = None, *, before: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """
        列出检查点（可选实现）
        """
        return iter([])
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        获取检查点元组
        """
        checkpoint = self.get(config)
        if checkpoint:
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=None
            )
        return None