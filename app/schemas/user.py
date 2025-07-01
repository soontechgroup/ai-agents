from pydantic import BaseModel, EmailStr
from typing import List, Optional

# 用户基础模型
class UserBase(BaseModel):
    name: str
    email: str
    gender: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None

class EmailUpdate(BaseModel):
    email: str

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    message: str

class PageInfo(BaseModel):
    current_page: int
    page_size: int
    total_users: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None

class UserListOut(BaseModel):
    users: List[UserOut]
    pagination: PageInfo

# JWT相关模型
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: UserOut
    expires_in: int

class TokenInfo(BaseModel):
    access_token: str
    token_type: str

class CurrentUserOut(UserOut):
    """当前用户信息输出模型"""
    pass 