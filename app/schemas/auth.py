from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreateRequest(BaseModel):
    """用户创建模式"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    """用户登录模式"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应模式"""
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


class TokenData(BaseModel):
    """令牌数据模式"""
    username: Optional[str] = None 