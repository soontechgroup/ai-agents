from fastapi import HTTPException, status
from app.core.models import User
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import UserCreateRequest, UserLoginRequest
from app.repositories.user_repository import UserRepository
from typing import Optional


class AuthService:
    """认证服务"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.user_repository.get_user_by_username(username)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.user_repository.get_user_by_email(email)
    
    def create_user(self, user_create: UserCreateRequest) -> User:
        """创建新用户"""
        # 检查用户名是否已存在（用户名必须唯一）
        if self.user_repository.get_user_by_username(user_create.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在（邮箱必须唯一）
        if self.user_repository.get_user_by_email(user_create.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
        
        # 创建新用户
        hashed_password = get_password_hash(user_create.password)
        user_data = {
            "username": user_create.username,
            "email": user_create.email,
            "hashed_password": hashed_password
        }
        
        return self.user_repository.create_user(user_data)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户身份"""
        user = self.user_repository.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def login_user(self, user_login: UserLoginRequest) -> dict:
        """用户登录"""
        user = self.authenticate_user(user_login.username, user_login.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户账户已被禁用"
            )
        
        # 创建访问令牌
        access_token = create_access_token(data={"sub": user.username})
        return {
            "access_token": access_token,
            "token_type": "bearer"
        } 