"""服务依赖注入"""
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.chroma_repository import ChromaRepository
from app.services.auth_service import AuthService
from app.services.chroma_service import ChromaService
from app.services.embedding_service import EmbeddingService
from app.services.langgraph_service import LangGraphService


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """获取用户仓库实例"""
    return UserRepository(db)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository)
) -> AuthService:
    """获取认证服务实例"""
    return AuthService(user_repository)


def get_chroma_repository() -> ChromaRepository:
    """获取 Chroma 仓库实例"""
    return ChromaRepository()


def get_embedding_service() -> EmbeddingService:
    """获取嵌入向量服务实例"""
    return EmbeddingService()


def get_chroma_service(
    chroma_repository: ChromaRepository = Depends(get_chroma_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> ChromaService:
    """获取 Chroma 服务实例"""
    return ChromaService(chroma_repository, embedding_service)


@lru_cache()
def get_langgraph_service() -> LangGraphService:
    """
    获取 LangGraph 服务单例实例
    使用 lru_cache 确保整个应用生命周期只创建一次
    使用 PostgreSQL checkpointer 避免双层缓存
    """
    from app.core.database import get_db
    return LangGraphService(db_session_factory=get_db)