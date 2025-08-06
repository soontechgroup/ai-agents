from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str = Field(..., description="管理员用户名")
    password: str = Field(..., description="管理员密码")


class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")


class AdminAccountInfo(BaseModel):
    """管理员账户信息"""
    id: int = Field(..., description="管理员ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    is_superuser: bool = Field(..., description="是否为超级管理员")
    is_active: bool = Field(..., description="账户是否激活")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class AdminAccountRequest(BaseModel):
    """获取管理员账户信息请求"""
    pass  # 空body


class AdminAccountUpdateRequest(BaseModel):
    """管理员账户更新请求"""
    email: Optional[EmailStr] = Field(None, description="新邮箱地址")
    
    
class AdminPasswordChangeRequest(BaseModel):
    """管理员密码修改请求"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码（至少6个字符）")
    

class AdminTokenRefreshRequest(BaseModel):
    """令牌刷新请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class AdminTokenRefreshResponse(BaseModel):
    """令牌刷新响应"""
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")