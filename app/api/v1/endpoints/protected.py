from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.jwt_auth import get_current_user
from app.schemas.user import UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter()

@router.get("/profile", response_model=UserOut)
async def get_protected_profile(current_user = Depends(get_current_user)):
    """获取当前用户的个人资料（受保护的接口）"""
    return current_user

@router.put("/profile", response_model=UserOut)
async def update_protected_profile(
    user_data: UserUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户的个人资料（受保护的接口）"""
    # 只允许更新当前用户自己的信息
    return UserService.update_user(db, current_user.id, user_data) 