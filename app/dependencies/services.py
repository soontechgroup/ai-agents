"""服务依赖注入"""
from fastapi import Depends
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """获取用户仓库实例"""
    return UserRepository(db)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository)
) -> AuthService:
    """获取认证服务实例"""
    return AuthService(user_repository)