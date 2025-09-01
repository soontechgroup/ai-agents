from fastapi import APIRouter, Depends
from app.schemas.auth import UserCreateRequest, UserLoginRequest, UserData, Token, CurrentUserRequest
from app.schemas.common_response import SuccessResponse
from app.services.auth_service import AuthService
from app.dependencies import get_auth_service
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil
from app.core.models import User

router = APIRouter()


@router.post("/register", response_model=SuccessResponse[UserData], summary="用户注册")
async def register(
    user_create: UserCreateRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户注册
    
    - **email**: 邮箱地址（必须唯一）
    - **password**: 密码
    """
    user = auth_service.create_user(user_create)
    return ResponseUtil.success(data=user, message="用户注册成功")


@router.post("/login", response_model=SuccessResponse[Token], summary="用户登录")
async def login(
    user_login: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户登录
    
    - **email**: 邮箱地址
    - **password**: 密码
    
    返回访问令牌
    """
    result = auth_service.login_user(user_login)
    token_data = Token(
        access_token=result["access_token"],
        token_type=result["token_type"]
    )
    return ResponseUtil.success(data=token_data, message="登录成功")


@router.post("/current", response_model=SuccessResponse[UserData], summary="获取当前用户信息")
async def get_current_user_info(
    request: CurrentUserRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户的信息
    
    需要在请求头中包含有效的Bearer令牌
    """
    return ResponseUtil.success(data=current_user, message="获取用户信息成功")

