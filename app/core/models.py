from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    digital_humans = relationship("DigitalHuman", back_populates="owner")


class DigitalHuman(Base):
    """数字人模板模型 - 可重用的AI助手模板"""
    __tablename__ = "digital_humans"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息 (对应前端Step 1)
    name = Column(String(100), nullable=False, comment="数字人名称")
    short_description = Column(String(200), nullable=True, comment="简短描述")
    detailed_description = Column(Text, nullable=True, comment="详细介绍")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    
    # 类型选择 (对应前端Step 2)
    type = Column(String(50), nullable=False, default="专业助手", comment="数字人类型")
    
    # 能力配置 (对应前端Step 3)
    skills = Column(JSON, nullable=True, comment="专业领域技能列表")
    personality = Column(JSON, nullable=True, comment="性格特征配置")
    conversation_style = Column(String(50), nullable=True, default="专业严谨", comment="对话风格")
    
    # AI配置参数
    temperature = Column(Float, default=0.7, comment="AI温度参数")
    max_tokens = Column(Integer, default=2048, comment="最大token数")
    system_prompt = Column(Text, nullable=True, comment="系统提示词")
    
    # 模板状态
    is_active = Column(Boolean, default=True, comment="模板是否启用（启用后可用于创建对话）")
    is_public = Column(Boolean, default=False, comment="是否公开模板")
    
    # 用户关联
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="digital_humans")
    
    # 关联关系
    conversations = relationship("Conversation", back_populates="digital_human_template")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_trained_at = Column(DateTime(timezone=True), nullable=True)


class Conversation(Base):
    """对话会话模型 - 使用数字人模板创建的具体对话实例"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False)
    title = Column(String(200), nullable=True, comment="会话标题")
    thread_id = Column(String(100), nullable=False, unique=True, comment="LangChain线程ID")
    status = Column(Enum("active", "archived", "deleted", name="conversation_status"), default="active", comment="会话状态")
    last_message_at = Column(DateTime(timezone=True), nullable=True, comment="最后消息时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    user = relationship("User")
    digital_human_template = relationship("DigitalHuman", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """消息记录模型"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, comment="对话ID")
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False, comment="消息角色")
    content = Column(Text, nullable=False, comment="消息内容")
    tokens_used = Column(Integer, nullable=True, comment="使用的token数量")
    message_metadata = Column(JSON, nullable=True, comment="消息元数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    conversation = relationship("Conversation", back_populates="messages")


class DigitalHumanTrainingMessage(Base):
    """数字人训练消息模型 - 记录训练过程中的对话和知识抽取"""
    __tablename__ = "digital_human_training_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum("user", "assistant", name="training_message_role"), nullable=False, comment="消息角色")
    content = Column(Text, nullable=False, comment="消息内容")
    extracted_knowledge = Column(JSON, nullable=True, comment="抽取的知识（实体和关系）")
    extraction_metadata = Column(JSON, nullable=True, comment="知识提取的溯源信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    digital_human = relationship("DigitalHuman")
    user = relationship("User") 