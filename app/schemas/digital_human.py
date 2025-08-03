from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from app.schemas.CommonResponse import PaginatedResponse, PaginationMeta


class PersonalityConfig(BaseModel):
    """性格特征配置"""
    professionalism: int = Field(default=80, ge=0, le=100, description="专业性 (0-100)")
    friendliness: int = Field(default=90, ge=0, le=100, description="友善度 (0-100)")
    humor: int = Field(default=60, ge=0, le=100, description="幽默感 (0-100)")


class DigitalHumanCreate(BaseModel):
    """创建数字人模板请求模型"""
    name: str = Field(..., max_length=100, description="数字人名称")
    short_description: Optional[str] = Field(None, max_length=200, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    type: str = Field(default="专业助手", description="数字人类型")
    skills: Optional[List[str]] = Field(default=[], description="专业领域技能")
    personality: Optional[PersonalityConfig] = Field(default_factory=PersonalityConfig, description="性格特征")
    conversation_style: Optional[str] = Field(default="专业严谨", description="对话风格")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2, description="AI温度参数")
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192, description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(default=False, description="是否公开模板")


class DigitalHumanUpdate(BaseModel):
    """更新数字人模板请求模型"""
    name: Optional[str] = Field(None, max_length=100, description="数字人名称")
    short_description: Optional[str] = Field(None, max_length=200, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    type: Optional[str] = Field(None, description="数字人类型")
    skills: Optional[List[str]] = Field(None, description="专业领域技能")
    personality: Optional[PersonalityConfig] = Field(None, description="性格特征")
    conversation_style: Optional[str] = Field(None, description="对话风格")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="AI温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(None, description="是否公开模板")
    is_active: Optional[bool] = Field(None, description="是否启用模板（启用后可用于对话）")


class DigitalHumanResponse(BaseModel):
    """数字人模板响应模型"""
    id: int = Field(..., description="数字人ID")
    name: str = Field(..., description="数字人名称")
    short_description: Optional[str] = Field(None, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    type: str = Field(..., description="数字人类型")
    skills: Optional[List[str]] = Field(None, description="专业领域技能")
    personality: Optional[Dict[str, int]] = Field(None, description="性格特征")
    conversation_style: Optional[str] = Field(None, description="对话风格")
    temperature: float = Field(..., description="AI温度参数")
    max_tokens: int = Field(..., description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_active: bool = Field(..., description="模板是否启用（启用后可用于创建对话）")
    is_public: bool = Field(..., description="是否公开模板")
    owner_id: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_trained_at: Optional[datetime] = Field(None, description="最后训练时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class DigitalHumanPageRequest(BaseModel):
    """数字人分页请求模型"""
    page: int = Field(default=1, ge=1, description="页码,从1开始")
    size: int = Field(default=10, ge=1, le=100, description="每页数量,最大100")
    search: Optional[str] = Field(None, description="搜索关键词(名称、描述)")


class DigitalHumanPageResponse(PaginatedResponse[List[DigitalHumanResponse]]):
    """数字人分页响应模型"""
    pass