from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.common_response import PaginatedResponse, PaginationMeta


class ConversationCreate(BaseModel):
    """创建对话请求模型"""
    digital_human_id: int = Field(..., description="数字人模板ID")
    title: Optional[str] = Field(None, max_length=200, description="对话标题")


class ConversationUpdate(BaseModel):
    """更新对话请求模型"""
    title: Optional[str] = Field(None, max_length=200, description="对话标题")


class ConversationResponse(BaseModel):
    """对话响应模型"""
    user_id: int = Field(..., description="用户ID")
    digital_human_id: int = Field(..., description="数字人模板ID")
    title: Optional[str] = Field(None, description="对话标题")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class MessageCreate(BaseModel):
    """创建消息请求模型"""
    content: str = Field(..., description="消息内容")


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: int = Field(..., description="消息ID")
    role: str = Field(..., description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息内容")
    tokens_used: Optional[int] = Field(None, description="使用的token数量")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元信息")
    memory: Optional[Dict[str, Any]] = Field(None, description="记忆搜索结果")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class ConversationWithMessages(ConversationResponse):
    """包含消息的对话响应模型"""
    messages: List[MessageResponse] = Field(default=[], description="消息列表")


class ConversationPageRequest(BaseModel):
    """对话分页请求模型"""
    page: int = Field(default=1, ge=1, description="页码,从1开始")
    size: int = Field(default=10, ge=1, le=100, description="每页数量,最大100")
    search: Optional[str] = Field(None, description="搜索关键词(标题)")
    status: Optional[str] = Field(None, description="过滤状态: active, archived, deleted")


class ConversationPageResponse(PaginatedResponse[List[ConversationResponse]]):
    """对话分页响应模型"""
    pass


class ChatStreamRequest(BaseModel):
    """聊天流式请求模型"""
    message: str = Field(..., description="用户消息内容")
    stream: bool = Field(default=True, description="是否流式响应")


class ChatStreamChunk(BaseModel):
    """聊天流式响应块"""
    type: str = Field(..., description="数据类型: message, token, error, done")
    content: str = Field(default="", description="内容")
    metadata: Optional[Dict] = Field(None, description="元数据")


class ConversationDetailRequest(BaseModel):
    """获取对话详情请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")


class ConversationUpdateRequest(BaseModel):
    """更新对话请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")
    title: Optional[str] = Field(None, max_length=200, description="对话标题")


class ConversationDeleteRequest(BaseModel):
    """删除对话请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")


class ConversationMessagesRequest(BaseModel):
    """获取对话消息请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")
    limit: Optional[int] = Field(None, description="消息数量限制")


class ConversationSendRequest(BaseModel):
    """发送消息请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")
    content: str = Field(..., description="消息内容")


class ConversationChatRequest(BaseModel):
    """聊天请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")
    message: str = Field(..., description="用户消息内容")
    stream: bool = Field(default=True, description="是否流式响应")


class ConversationClearRequest(BaseModel):
    """清除对话历史请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")