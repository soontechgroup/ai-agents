from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import SuccessResponse, ErrorResponse
from app.services.user_service import UserService
from app.core.database import get_db
from app.core.models import User
from app.utils.response import ResponseUtil

router = APIRouter(prefix="/api/v1")


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """获取用户服务实例"""
    return UserService(db)


@router.post("/users", response_model=SuccessResponse[UserResponse], summary="创建用户")
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


@router.get("/users", response_model=SuccessResponse[List[UserResponse]], summary="获取用户列表")
async def get_users(
    user_service: UserService = Depends(get_user_service)
):
    """
    获取所有用户列表
    """
    users = user_service.get_all_users()
    return ResponseUtil.success(data=users, message="获取用户列表成功")


@router.get("/users/{user_id}", response_model=SuccessResponse[UserResponse], summary="获取用户详情")
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """
    根据ID获取用户详情
    
    - **user_id**: 用户ID
    """
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return ResponseUtil.success(data=user, message="获取用户详情成功")


@router.put("/users/{user_id}", response_model=SuccessResponse[UserResponse], summary="更新用户")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用户信息
    
    - **user_id**: 用户ID
    - 其他字段均为可选，只更新提供的字段
    """
    user = user_service.update_user(user_id, user_data)
    return ResponseUtil.success(data=user, message="用户更新成功")


@router.delete("/users/{user_id}", response_model=SuccessResponse[None], summary="删除用户")
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """
    删除用户
    
    - **user_id**: 用户ID
    """
    user_service.delete_user(user_id)
    return ResponseUtil.success(message="用户删除成功")




@router.get("/", summary="根路径")
async def read_root(db: Session = Depends(get_db)):
    """
    根路径，返回所有用户信息
    """
    users = db.query(User).all()
    users_data = [{"id": u.id, "username": u.username, "email": u.email} for u in users]
    return {"users": users_data}