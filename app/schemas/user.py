from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime


class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    password_hash: str = Field(..., description="密码哈希")


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[str] = Field(None, description="邮箱地址")
    password_hash: Optional[str] = Field(None, description="密码哈希")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    password_hash: str = Field(..., description="密码哈希")
    created_at: str = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class UserAuth(BaseModel):
    """用户注册模型"""
    name: str = Field(..., description="姓名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class UserLogin(BaseModel):
    """用户登录模型"""
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class UserMeResponse(BaseModel):
    """当前用户信息响应模型"""
    id: int = Field(..., description="用户ID")
    name: str = Field(..., description="姓名")
    email: str = Field(..., description="邮箱地址")


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: Literal[True] = True
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(..., description="令牌类型")
    user: UserMeResponse = Field(..., description="用户信息")


class TokenResponse(BaseModel):
    """令牌响应模型"""
    success: Literal[True] = True
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(..., description="令牌类型")