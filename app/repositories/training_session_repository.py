from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Tuple
from datetime import datetime
from app.core.models import TrainingSession, DigitalHumanTrainingMessage, DigitalHuman
from app.core.logger import logger


class TrainingSessionRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(
        self,
        digital_human_id: int,
        user_id: int,
        thread_id: str,
        session_type: str = "knowledge_input"
    ) -> TrainingSession:
        session = TrainingSession(
            digital_human_id=digital_human_id,
            user_id=user_id,
            thread_id=thread_id,
            session_type=session_type,
            status="in_progress"
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"创建训练会话: ID={session.id}, 数字人={digital_human_id}, 用户={user_id}")
        return session
    
    def get_session_by_id(
        self,
        session_id: int,
        user_id: Optional[int] = None
    ) -> Optional[TrainingSession]:
        query = self.db.query(TrainingSession).filter(
            TrainingSession.id == session_id
        )
        
        if user_id:
            query = query.filter(TrainingSession.user_id == user_id)
        
        return query.first()
    
    def get_session_by_thread_id(
        self,
        thread_id: str
    ) -> Optional[TrainingSession]:
        return self.db.query(TrainingSession).filter(
            TrainingSession.thread_id == thread_id
        ).first()
    
    def get_active_session(
        self,
        digital_human_id: int,
        user_id: int
    ) -> Optional[TrainingSession]:
        return self.db.query(TrainingSession).filter(
            and_(
                TrainingSession.digital_human_id == digital_human_id,
                TrainingSession.user_id == user_id,
                TrainingSession.status == "in_progress"
            )
        ).order_by(desc(TrainingSession.started_at)).first()
    
    def update_session_status(
        self,
        session_id: int,
        status: str,
        knowledge_summary: Optional[dict] = None
    ) -> Optional[TrainingSession]:
        session = self.get_session_by_id(session_id)
        if not session:
            return None
        
        session.status = status
        
        if status == "completed":
            session.completed_at = datetime.now()
        elif status == "applied":
            session.applied_at = datetime.now()
        
        if knowledge_summary:
            session.knowledge_summary = knowledge_summary
        
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"更新训练会话状态: ID={session_id}, 状态={status}")
        return session
    
    def update_session_statistics(
        self,
        session_id: int,
        total_messages: Optional[int] = None,
        extracted_entities: Optional[int] = None,
        extracted_relations: Optional[int] = None
    ) -> Optional[TrainingSession]:
        session = self.get_session_by_id(session_id)
        if not session:
            return None
        
        if total_messages is not None:
            session.total_messages = total_messages
        if extracted_entities is not None:
            session.extracted_entities = extracted_entities
        if extracted_relations is not None:
            session.extracted_relations = extracted_relations
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_user_sessions(
        self,
        user_id: int,
        digital_human_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[TrainingSession], int]:
        query = self.db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id
        )
        
        if digital_human_id:
            query = query.filter(TrainingSession.digital_human_id == digital_human_id)
        
        if status:
            query = query.filter(TrainingSession.status == status)
        
        total = query.count()
        
        sessions = query.order_by(
            desc(TrainingSession.started_at)
        ).offset(offset).limit(limit).all()
        
        return sessions, total
    
    def add_message_to_session(
        self,
        session_id: int,
        digital_human_id: int,
        user_id: int,
        role: str,
        content: str,
        extracted_knowledge: Optional[dict] = None,
        extraction_metadata: Optional[dict] = None
    ) -> DigitalHumanTrainingMessage:
        message = DigitalHumanTrainingMessage(
            session_id=session_id,
            digital_human_id=digital_human_id,
            user_id=user_id,
            role=role,
            content=content,
            extracted_knowledge=extracted_knowledge,
            extraction_metadata=extraction_metadata
        )
        
        self.db.add(message)
        
        session = self.get_session_by_id(session_id)
        if session:
            session.total_messages = (session.total_messages or 0) + 1
        
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_session_messages(
        self,
        session_id: int,
        limit: Optional[int] = None
    ) -> List[DigitalHumanTrainingMessage]:
        query = self.db.query(DigitalHumanTrainingMessage).filter(
            DigitalHumanTrainingMessage.session_id == session_id
        ).order_by(DigitalHumanTrainingMessage.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def complete_session_with_summary(
        self,
        session_id: int,
        entities_count: int,
        relations_count: int,
        knowledge_summary: dict
    ) -> Optional[TrainingSession]:
        session = self.get_session_by_id(session_id)
        if not session:
            return None
        
        session.status = "completed"
        session.completed_at = datetime.now()
        session.extracted_entities = entities_count
        session.extracted_relations = relations_count
        session.knowledge_summary = knowledge_summary
        
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"完成训练会话: ID={session_id}, 实体={entities_count}, 关系={relations_count}")
        return session
    
    def commit(self):
        """提交事务"""
        self.db.commit()
    
    def rollback(self):
        """回滚事务"""
        self.db.rollback()