from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import UserCreateRequest, UserLoginRequest, UserData, Token
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_active_user, get_current_user
from app.utils.response import ResponseUtil
from app.core.models import User

router = APIRouter()


@router.post("/register", response_model=SuccessResponse[UserData], summary="用户注册")
async def register(
    user_create: UserCreateRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名（必须唯一）
    - **email**: 邮箱地址（允许重复）
    - **password**: 密码
    - **full_name**: 全名（可选）
    """
    user = AuthService.create_user(db, user_create)
    return ResponseUtil.success(data=user, message="用户注册成功")


@router.post("/login", response_model=SuccessResponse[Token], summary="用户登录")
async def login(
    user_login: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回访问令牌
    """
    result = AuthService.login_user(db, user_login)
    token_data = Token(
        access_token=result["access_token"],
        token_type=result["token_type"]
    )
    return ResponseUtil.success(data=token_data, message="登录成功")



@router.get("/me", response_model=SuccessResponse[UserData], summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户的信息
    
    需要在请求头中包含有效的Bearer令牌
    """
    return ResponseUtil.success(data=current_user, message="获取用户信息成功")

