from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.chroma_repository import ChromaRepository
from app.repositories.training_message_repository import TrainingMessageRepository
from app.repositories.training_session_repository import TrainingSessionRepository
from app.services.auth_service import AuthService
from app.services.chroma_service import ChromaService
from app.services.embedding_service import EmbeddingService
from app.services.langgraph_service import LangGraphService
from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.digital_human_training_service import DigitalHumanTrainingService
from app.services.graph_service import GraphService
from app.services.conversation_service import ConversationService
from app.dependencies.graph import get_graph_service


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository)
) -> AuthService:
    return AuthService(user_repository)


def get_chroma_repository() -> ChromaRepository:
    return ChromaRepository()


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def get_chroma_service(
    chroma_repository: ChromaRepository = Depends(get_chroma_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> ChromaService:
    return ChromaService(chroma_repository, embedding_service)


@lru_cache()
def get_langgraph_service() -> LangGraphService:
    from app.core.database import get_db
    return LangGraphService(db_session_factory=get_db)


def get_knowledge_extractor() -> KnowledgeExtractor:
    return KnowledgeExtractor()


def get_conversation_service(
    db: Session = Depends(get_db),
    langgraph_service: LangGraphService = Depends(get_langgraph_service)
) -> ConversationService:
    return ConversationService(db, langgraph_service)


def get_training_message_repository(
    db: Session = Depends(get_db)
) -> TrainingMessageRepository:
    return TrainingMessageRepository(db)


def get_training_session_repository(
    db: Session = Depends(get_db)
) -> TrainingSessionRepository:
    return TrainingSessionRepository(db)


def get_digital_human_training_service(
    training_message_repo: TrainingMessageRepository = Depends(get_training_message_repository),
    training_session_repo: TrainingSessionRepository = Depends(get_training_session_repository),
    knowledge_extractor: KnowledgeExtractor = Depends(get_knowledge_extractor),
    graph_service: GraphService = Depends(get_graph_service)
) -> DigitalHumanTrainingService:
    from app.core.database import get_db
    return DigitalHumanTrainingService(
        training_message_repo, 
        training_session_repo, 
        knowledge_extractor, 
        graph_service,
        db_session_factory=get_db  # 传入数据库会话工厂
    )