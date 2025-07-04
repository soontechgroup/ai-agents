from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, Any
from datetime import datetime

# 定义泛型类型
T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """通用响应模式"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="操作成功", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class SuccessResponse(BaseResponse[T]):
    """成功响应"""
    code: int = Field(default=200, description="成功状态码")
    message: str = Field(default="操作成功", description="成功消息")


class ErrorResponse(BaseResponse[None]):
    """错误响应"""
    code: int = Field(default=400, description="错误状态码")
    message: str = Field(default="操作失败", description="错误消息")
    data: None = Field(default=None, description="错误时数据为空")
