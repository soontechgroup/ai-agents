from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: Literal["user", "assistant", "system"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容", min_length=1)
    timestamp: Optional[datetime] = Field(default=None, description="消息时间戳")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=4000)
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=[], 
        description="对话历史记录",
        max_items=50
    )
    model: Optional[str] = Field(default=None, description="指定使用的模型")
    temperature: Optional[float] = Field(
        default=None, 
        description="温度参数，控制响应的随机性",
        ge=0.0,
        le=2.0
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="最大token数量",
        gt=0,
        le=4000
    )


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str = Field(..., description="AI回复内容")
    role: str = Field(default="assistant", description="回复角色")
    model: str = Field(..., description="使用的模型")
    usage: Optional[dict] = Field(default=None, description="Token使用情况")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class ConversationSession(BaseModel):
    """对话会话模型"""
    session_id: str = Field(..., description="会话ID")
    messages: List[ChatMessage] = Field(default=[], description="消息列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class ChatSettings(BaseModel):
    """聊天设置模型"""
    model: str = Field(default="gpt-3.5-turbo", description="默认使用的模型")
    temperature: float = Field(default=0.7, description="默认温度参数", ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, description="默认最大token数", gt=0, le=4000)
    system_prompt: Optional[str] = Field(
        default="你是一个有帮助的AI助手，请用中文回答问题。",
        description="系统提示词"
    )
