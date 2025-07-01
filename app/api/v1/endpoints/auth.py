from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_active_user, get_current_user
from app.core.models import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名（必须唯一）
    - **email**: 邮箱地址（必须唯一）
    - **password**: 密码
    - **full_name**: 全名（可选）
    """
    user = AuthService.create_user(db, user_create)
    return user


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回访问令牌
    """
    try:
        result = AuthService.login_user(db, user_login)
        return {
            "access_token": result["access_token"],
            "token_type": result["token_type"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户的信息
    
    需要在请求头中包含有效的Bearer令牌
    """
    return current_user


@router.get("/protected", summary="受保护的测试端点")
async def protected_route(
    current_user: User = Depends(get_current_active_user)
):
    """
    受保护的测试端点
    
    需要有效的JWT令牌才能访问
    """
    return {
        "message": f"你好 {current_user.username}！这是一个受保护的端点。",
        "user_id": current_user.id,
        "is_superuser": current_user.is_superuser
    } 