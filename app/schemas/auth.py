from pydantic import BaseModel, EmailStr
from pydantic import BaseModel, EmailStr, Field, constr
from typing import Optional
from datetime import datetime


class UserCreateRequest(BaseModel):
    """用户创建模式"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: constr(min_length=6) = Field(..., description="密码（最少6个字符）")



class UserLoginRequest(BaseModel):
    """用户登录模式"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class UserData(BaseModel):
    """用户数据模式"""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class CurrentUserRequest(BaseModel):
    """获取当前用户请求模式"""
    pass


class Token(BaseModel):
    """令牌响应模式"""
    access_token: str
    token_type: str
