from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.models import User
from app.schemas.user import UserCreate, UserUpdate
from typing import List, Optional, Dict, Any


class UserService:
    """用户服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查邮箱是否已存在
        if self.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
        
        
        # 创建用户
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=user_data.password_hash
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """更新用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 更新数据
        update_data = user_data.dict(exclude_unset=True)
        
        # 检查邮箱是否重复
        if 'email' in update_data:
            existing_user = self.get_user_by_email(update_data['email'])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已存在"
                )
        
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        self.db.delete(user)
        self.db.commit()
        
        return True
    
