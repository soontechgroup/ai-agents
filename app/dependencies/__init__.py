"""依赖注入模块"""
from .database import get_db
from .services import get_user_repository, get_auth_service

__all__ = [
    "get_db",
    "get_user_repository", 
    "get_auth_service"
]