from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.core.database import get_db, User
from app.core.jwt_auth import get_current_user
from app.schemas.user import (
    UserCreate, UserUpdate, EmailUpdate, UserOut, 
    MessageOut, UserListOut, PageInfo
)
from app.services.user_service import UserService

router = APIRouter()

@router.get("/", response_model=UserListOut)
async def page_users(
    page: int = Query(1, ge=1, description="Page number"), 
    size: int = Query(50, ge=1, le=100, description="Page size"), 
    name: Optional[str] = Query(None, description="Filter by name"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    field: Optional[str] = Query(None, description="Search field"),
    db: Session = Depends(get_db)
):
    """获取用户列表（支持分页和搜索）"""
    
    # 构建查询
    query = db.query(User)
    
    # 应用筛选条件
    if name:
        query = query.filter(User.name.ilike(f"%{name}%"))
    
    if gender:
        query = query.filter(User.gender.ilike(f"%{gender}%"))
    
    # 应用搜索条件
    if keyword:
        if field:
            # 验证指定的字段
            valid_fields = ["name", "email", "gender"]
            if field not in valid_fields:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid search field"
                )
            
            # 在指定字段中搜索
            if field == "name":
                query = query.filter(User.name.ilike(f"%{keyword}%"))
            elif field == "email":
                query = query.filter(User.email.ilike(f"%{keyword}%"))
            elif field == "gender":
                query = query.filter(User.gender.ilike(f"%{keyword}%"))
        else:
            # 在所有字段中搜索
            query = query.filter(
                (User.name.ilike(f"%{keyword}%")) |
                (User.email.ilike(f"%{keyword}%")) |
                (User.gender.ilike(f"%{keyword}%"))
            )
    
    # 计算总数
    total_found = query.count()
    
    # 应用分页
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()
    
    total_pages = -(-total_found // size) if total_found > 0 else 1  # 向上取整
    
    pagination = PageInfo(
        current_page=page,
        page_size=size,
        total_users=total_found,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )
    
    return UserListOut(users=users, pagination=pagination)

@router.post("/", response_model=UserOut)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建用户"""
    return UserService.create_user(db, user)

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """根据ID获取用户"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """更新用户信息"""
    return UserService.update_user(db, user_id, user)

@router.delete("/{user_id}", response_model=MessageOut)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户"""
    UserService.delete_user(db, user_id)
    return MessageOut(message="User deleted successfully")

@router.patch("/{user_id}/email", response_model=UserOut)
async def update_user_email(
    user_id: int, 
    email_data: EmailUpdate, 
    db: Session = Depends(get_db)
):
    """更新用户邮箱"""
    # 检查邮箱是否已被其他用户使用
    existing_user = db.query(User).filter(
        User.email == email_data.email,
        User.id != user_id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    # 更新邮箱
    user_update = UserUpdate(email=email_data.email)
    return UserService.update_user(db, user_id, user_update) 