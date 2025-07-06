from pydantic import BaseModel, EmailStr
from pydantic import BaseModel, EmailStr, Field, constr
from typing import Optional
from datetime import datetime


class UserCreateRequest(BaseModel):
    """用户创建模式"""
    username: constr(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$') = Field(..., description="用户名（3-50字符，只允许字母、数字、下划线和连字符）")
    email: EmailStr = Field(..., description="邮箱地址")
    password: constr(min_length=6) = Field(..., description="密码（最少6个字符）")
    full_name: Optional[str] = Field(None, max_length=100, description="全名（可选，最多100字符）")


class UserLoginRequest(BaseModel):
    """用户登录模式"""
    username: str
    password: str


class UserData(BaseModel):
    """用户数据模式"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """令牌响应模式"""
    access_token: str
    token_type: str
