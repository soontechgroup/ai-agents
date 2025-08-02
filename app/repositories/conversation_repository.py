from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Tuple
from app.core.models import Conversation, Message, DigitalHuman
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationPageRequest
from datetime import datetime


class ConversationRepository:
    """对话数据访问层"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(
        self,
        conversation_data: ConversationCreate,
        user_id: int,
        thread_id: str
    ) -> Conversation:
        """创建新对话"""
        # 验证数字人模板是否存在且用户有权限使用
        digital_human = self.db.query(DigitalHuman).filter(
            and_(
                DigitalHuman.id == conversation_data.digital_human_id,
                or_(
                    DigitalHuman.owner_id == user_id,  # 用户自己的模板
                    DigitalHuman.is_public == True     # 公开模板
                ),
                DigitalHuman.is_active == True
            )
        ).first()
        
        if not digital_human:
            raise ValueError("数字人模板不存在或无权限访问")
        
        # 生成默认标题
        title = conversation_data.title or f"与{digital_human.name}的对话"
        
        # 创建对话
        conversation = Conversation(
            user_id=user_id,
            digital_human_id=conversation_data.digital_human_id,
            title=title,
            thread_id=thread_id,
            status="active"
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def get_conversation_by_id(
        self,
        conversation_id: int,
        user_id: int
    ) -> Optional[Conversation]:
        """根据ID获取对话"""
        return self.db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.status != "deleted"
            )
        ).first()
    
    def get_conversations_paginated(
        self,
        page_request: ConversationPageRequest,
        user_id: int
    ) -> Tuple[List[Conversation], int]:
        """分页获取用户对话列表"""
        query = self.db.query(Conversation).filter(
            and_(
                Conversation.user_id == user_id,
                Conversation.status != "deleted"
            )
        )
        
        # 搜索过滤
        if page_request.search:
            search_term = f"%{page_request.search}%"
            query = query.filter(Conversation.title.ilike(search_term))
        
        # 状态过滤
        if page_request.status:
            query = query.filter(Conversation.status == page_request.status)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        conversations = query.order_by(desc(Conversation.last_message_at), desc(Conversation.updated_at)).offset(
            (page_request.page - 1) * page_request.size
        ).limit(page_request.size).all()
        
        return conversations, total
    
    def update_conversation(
        self,
        conversation_id: int,
        conversation_data: ConversationUpdate,
        user_id: int
    ) -> Optional[Conversation]:
        """更新对话"""
        conversation = self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return None
        
        # 更新字段
        if conversation_data.title is not None:
            conversation.title = conversation_data.title
        
        if conversation_data.status is not None:
            conversation.status = conversation_data.status
        
        conversation.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话（软删除）"""
        conversation = self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return False
        
        conversation.status = "deleted"
        conversation.updated_at = datetime.now()
        
        self.db.commit()
        return True
    
    def get_conversation_by_thread_id(
        self,
        thread_id: str,
        user_id: int
    ) -> Optional[Conversation]:
        """根据线程ID获取对话"""
        return self.db.query(Conversation).filter(
            and_(
                Conversation.thread_id == thread_id,
                Conversation.user_id == user_id,
                Conversation.status != "deleted"
            )
        ).first()


class MessageRepository:
    """消息数据访问层"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> Message:
        """创建消息"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            message_metadata=metadata
        )
        
        self.db.add(message)
        
        # 更新对话的最后消息时间
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.last_message_at = datetime.now()
            conversation.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """获取对话的所有消息"""
        query = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 20
    ) -> List[Message]:
        """获取最近的消息"""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
    
    def delete_conversation_messages(self, conversation_id: int) -> bool:
        """删除对话的所有消息"""
        try:
            self.db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).delete()
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False