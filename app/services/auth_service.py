from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.models import User
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import UserCreateRequest, UserLoginRequest
from typing import Optional


class AuthService:
    """认证服务"""
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreateRequest) -> User:
        """创建新用户"""
        # 检查用户名是否已存在
        if AuthService.get_user_by_username(db, user_create.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        if AuthService.get_user_by_email(db, user_create.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
        
        # 创建新用户
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """验证用户身份"""
        user = AuthService.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    @staticmethod
    def login_user(db: Session, user_login: UserLoginRequest) -> dict:
        """用户登录"""
        user = AuthService.authenticate_user(db, user_login.username, user_login.password)
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
            "token_type": "bearer",
            "user": user
        } 