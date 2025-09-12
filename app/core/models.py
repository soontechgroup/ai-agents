from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, ForeignKey, Enum, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    digital_humans = relationship("DigitalHuman", back_populates="owner")


class DigitalHuman(Base):
    __tablename__ = "digital_humans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    short_description = Column(String(200), nullable=True)
    detailed_description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    type = Column(String(50), nullable=False, default="专业助手")
    skills = Column(JSON, nullable=True)
    personality = Column(JSON, nullable=True)
    conversation_style = Column(String(50), nullable=True, default="专业严谨")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_trained_at = Column(DateTime(timezone=True), nullable=True)
    
    owner = relationship("User", back_populates="digital_humans")
    conversations = relationship("Conversation", back_populates="digital_human_template")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False)
    title = Column(String(200), nullable=True)
    thread_id = Column(String(100), nullable=False, unique=True)
    status = Column(Enum("active", "archived", "deleted", name="conversation_status"), default="active")
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User")
    digital_human_template = relationship("DigitalHuman", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")


class TrainingSession(Base):
    __tablename__ = "training_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, unique=True, index=True)
    
    session_type = Column(String(50), default="knowledge_input")
    status = Column(Enum("in_progress", "completed", "applied", "cancelled", name="training_status"), default="in_progress")
    
    total_messages = Column(Integer, default=0)
    extracted_entities = Column(Integer, default=0)
    extracted_relations = Column(Integer, default=0)
    knowledge_summary = Column(JSON, nullable=True)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    digital_human = relationship("DigitalHuman")
    user = relationship("User")
    training_messages = relationship("DigitalHumanTrainingMessage", back_populates="session")


class DigitalHumanTrainingMessage(Base):
    __tablename__ = "digital_human_training_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=True, index=True)
    role = Column(Enum("user", "assistant", name="training_message_role"), nullable=False)
    content = Column(Text, nullable=False)
    extracted_knowledge = Column(JSON, nullable=True)
    extraction_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    digital_human = relationship("DigitalHuman")
    user = relationship("User")
    session = relationship("TrainingSession", back_populates="training_messages")


class ConversationCheckpoint(Base):
    __tablename__ = "conversation_checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    parent_version = Column(Integer, nullable=True)
    checkpoint_data = Column(JSON, nullable=False)
    channel_values = Column(JSON, nullable=False)
    channel_versions = Column(JSON, nullable=True)
    checkpoint_metadata = Column("metadata", JSON, nullable=True)
    task_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation")
    
    __table_args__ = (
        Index('idx_thread_version', 'thread_id', 'version'),
        UniqueConstraint('thread_id', 'version', name='uq_thread_version'),
    )