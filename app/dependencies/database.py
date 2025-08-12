"""数据库相关依赖"""
from app.core.database import SessionLocal
from app.core.mongodb import get_client
from motor.motor_asyncio import AsyncIOMotorClient


def get_db():
    """获取 MySQL 数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_mongo_client() -> AsyncIOMotorClient:
    """
    获取 MongoDB 客户端实例（用于依赖注入）
    
    Returns:
        MongoDB 客户端实例
        
    Raises:
        RuntimeError: 如果 MongoDB 客户端未初始化
    """
    return get_client()