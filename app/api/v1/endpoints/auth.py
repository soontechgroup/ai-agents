from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.jwt_auth import JWTToken, get_current_user
from app.schemas.user import (
    LoginRequest, LoginResponse, TokenInfo, 
    CurrentUserOut, UserCreate
)
from app.services.user_service import UserService
from app.core.jwt_auth import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    # 验证用户凭据
    user = UserService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = JWTToken.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_info=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 秒数
    )

@router.get("/me", response_model=CurrentUserOut)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

@router.post("/refresh", response_model=TokenInfo)
async def refresh_token(current_user = Depends(get_current_user)):
    """刷新访问令牌"""
    # 生成新的访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = JWTToken.create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=access_token_expires
    )
    
    return TokenInfo(
        access_token=access_token,
        token_type="bearer"
    )

@router.post("/register", response_model=LoginResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 创建用户
    user = UserService.create_user(db, user_data)
    
    # 自动登录，生成令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = JWTToken.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_info=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    ) 