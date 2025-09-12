from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from app.core.models import DigitalHumanTrainingMessage
from app.core.logger import logger


class TrainingMessageRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_training_message(
        self,
        digital_human_id: int,
        user_id: int,
        role: str,
        content: str,
        extracted_knowledge: Optional[Dict[str, Any]] = None,
        extraction_metadata: Optional[Dict[str, Any]] = None
    ) -> DigitalHumanTrainingMessage:
        training_message = DigitalHumanTrainingMessage(
            digital_human_id=digital_human_id,
            user_id=user_id,
            role=role,
            content=content,
            extracted_knowledge=extracted_knowledge,
            extraction_metadata=extraction_metadata
        )
        
        self.db.add(training_message)
        self.db.flush()
        
        logger.info(f"创建训练消息: {role} - 数字人ID: {digital_human_id}")
        return training_message
    
    def get_training_messages(
        self,
        digital_human_id: int,
        user_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[DigitalHumanTrainingMessage]:
        query = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id
        )
        
        if user_id:
            query = query.filter(DigitalHumanTrainingMessage.user_id == user_id)
        
        query = query.order_by(DigitalHumanTrainingMessage.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update_message_knowledge(
        self,
        message_id: int,
        extracted_knowledge: Dict[str, Any],
        extraction_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        message = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.id == message_id
        ).first()
        
        if not message:
            logger.warning(f"训练消息不存在: {message_id}")
            return False
        
        message.extracted_knowledge = extracted_knowledge
        if extraction_metadata:
            message.extraction_metadata = extraction_metadata
        
        self.db.flush()
        logger.info(f"更新训练消息知识: {message_id}")
        return True
    
    def get_messages_with_knowledge(
        self,
        digital_human_id: int,
        limit: Optional[int] = 100
    ) -> List[DigitalHumanTrainingMessage]:
        return self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id,
            DigitalHumanTrainingMessage.extracted_knowledge.isnot(None)
        ).order_by(
            DigitalHumanTrainingMessage.created_at.desc()
        ).limit(limit).all()
    
    def get_training_statistics(self, digital_human_id: int) -> Dict[str, Any]:
        total_messages = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id
        ).count()
        
        messages_with_knowledge = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id,
            DigitalHumanTrainingMessage.extracted_knowledge.isnot(None)
        ).count()
        
        user_messages = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id,
            DigitalHumanTrainingMessage.role == "user"
        ).count()
        
        assistant_messages = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id,
            DigitalHumanTrainingMessage.role == "assistant"
        ).count()
        
        return {
            "total_messages": total_messages,
            "messages_with_knowledge": messages_with_knowledge,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "knowledge_extraction_rate": (
                messages_with_knowledge / total_messages * 100 
                if total_messages > 0 else 0
            )
        }
    
    def get_training_messages_paginated(
        self,
        digital_human_id: int,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[DigitalHumanTrainingMessage], int]:
        """分页获取训练消息"""
        query = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.digital_human_id == digital_human_id
        )
        
        total = query.count()
        
        messages = query.order_by(
            DigitalHumanTrainingMessage.created_at.desc()
        ).offset((page - 1) * size).limit(size).all()

        logger.info(f"分页获取训练消息: 数字人ID={digital_human_id}, 页码={page}, 每页={size}, 总数={total}")
        
        return messages, total
    
    def commit(self):
        self.db.commit()
    
    def rollback(self):
        self.db.rollback()