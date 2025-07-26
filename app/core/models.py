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
    """数字人模型 - 完全匹配前端DigitalHumanData接口"""
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
    
    
    # 用户关联
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="digital_humans")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_trained_at = Column(DateTime(timezone=True), nullable=True)


class Session(Base):
    """会话模型"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False)
    title = Column(String(200), nullable=True, comment="会话标题")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    user = relationship("User")
    digital_human = relationship("DigitalHuman")
    chats = relationship("DigitalHumanChat", back_populates="session")


class DigitalHumanChat(Base):
    """数字人对话记录"""
    __tablename__ = "digital_human_chats"
    
    id = Column(Integer, primary_key=True, index=True)
    digital_human_id = Column(Integer, ForeignKey("digital_humans.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, comment="会话ID")
    message_type = Column(Enum("user", "assistant", name="message_type"), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True, comment="消息元数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    digital_human = relationship("DigitalHuman")
    user = relationship("User")
    session = relationship("Session", back_populates="chats") 