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
from app.services.conversation_service import ConversationService


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


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """获取嵌入向量服务实例（应用级缓存）
    使用 lru_cache 避免重复验证 API key
    """
    return EmbeddingService()


def get_chroma_service(
    chroma_repository: ChromaRepository = Depends(get_chroma_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> ChromaService:
    """获取 Chroma 服务实例"""
    return ChromaService(chroma_repository, embedding_service)


@lru_cache()
def get_langgraph_service() -> LangGraphService:
    """获取 LangGraph 服务实例（应用级缓存）
    使用 lru_cache 因为：
    1. 初始化时会验证 OpenAI API key（网络请求）
    2. 包含 MemorySaver 有状态组件，需要跨请求保持对话历史
    """
    return LangGraphService()


def get_conversation_service(
    db: Session = Depends(get_db),
    langgraph_service: LangGraphService = Depends(get_langgraph_service)
) -> ConversationService:
    """获取对话服务实例"""
    return ConversationService(db, langgraph_service)