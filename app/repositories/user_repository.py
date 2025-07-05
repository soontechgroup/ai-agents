from sqlalchemy.orm import Session
from app.core.models import User
from app.schemas.auth import UserCreateRequest
from typing import Optional


class UserRepository:
    """用户数据访问层"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def create_user(self, user_data: dict) -> User:
        """创建新用户"""
        db_user = User(**user_data)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def update_user(self, user: User, user_data: dict) -> User:
        """更新用户信息"""
        for key, value in user_data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user: User) -> bool:
        """删除用户"""
        self.db.delete(user)
        self.db.commit()
        return True 