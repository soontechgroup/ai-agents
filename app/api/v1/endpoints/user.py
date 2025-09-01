from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListRequest, UserDetailRequest, UserUpdateRequest, UserDeleteRequest
from app.schemas.common_response import SuccessResponse, ErrorResponse
from app.services.user_service import UserService
from app.core.database import get_db
from app.core.models import User
from app.utils.response import ResponseUtil

router = APIRouter()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """获取用户服务实例"""
    return UserService(db)


@router.post("/create", response_model=SuccessResponse[UserResponse], summary="创建用户")
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    创建用户
    
    - **username**: 用户名（必须唯一）
    - **email**: 邮箱地址（必须唯一）
    - **password_hash**: 密码哈希
    """
    user = user_service.create_user(user_data)
    return ResponseUtil.success(data=user, message="用户创建成功")


@router.post("/list", response_model=SuccessResponse[List[UserResponse]], summary="获取用户列表")
async def get_users(
    request: UserListRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    获取所有用户列表
    """
    users = user_service.get_all_users()
    return ResponseUtil.success(data=users, message="获取用户列表成功")


@router.post("/detail", response_model=SuccessResponse[UserResponse], summary="获取用户详情")
async def get_user(
    request: UserDetailRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    根据ID获取用户详情
    
    - **id**: 用户ID
    """
    user = user_service.get_user_by_id(request.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return ResponseUtil.success(data=user, message="获取用户详情成功")


@router.post("/update", response_model=SuccessResponse[UserResponse], summary="更新用户")
async def update_user(
    request: UserUpdateRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用户信息
    
    - **id**: 用户ID
    - 其他字段均为可选，只更新提供的字段
    """
    # 将UserUpdateRequest转换为UserUpdate（不包含id）
    update_data = UserUpdate(**request.model_dump(exclude={'id'}))
    user = user_service.update_user(request.id, update_data)
    return ResponseUtil.success(data=user, message="用户更新成功")


@router.post("/delete", response_model=SuccessResponse[None], summary="删除用户")
async def delete_user(
    request: UserDeleteRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    删除用户
    
    - **id**: 用户ID
    """
    user_service.delete_user(request.id)
    return ResponseUtil.success(message="用户删除成功")




