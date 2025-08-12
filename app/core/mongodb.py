from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional, List
from loguru import logger


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database_name: Optional[str] = None  # 只保存数据库名，不保存实例


mongodb = MongoDB()


async def init_mongodb(
    mongodb_url: str,
    database_name: str,
    document_models: List
):
    """
    初始化 MongoDB 连接和 Beanie ODM
    
    Args:
        mongodb_url: MongoDB 连接字符串
        database_name: 数据库名称
        document_models: Beanie 文档模型列表
    """
    try:
        logger.info("正在连接 MongoDB...")
        
        # 创建 Motor 客户端
        mongodb.client = AsyncIOMotorClient(mongodb_url)
        
        # 保存数据库名称
        mongodb.database_name = database_name
        
        # 初始化 Beanie（如果有模型）
        if document_models:
            database = mongodb.client[database_name]
            await init_beanie(
                database=database,
                document_models=document_models
            )
        
        # 测试连接
        await mongodb.client.admin.command('ping')
        logger.info(f"MongoDB 连接成功: {database_name}")
        
    except Exception as e:
        logger.error(f"MongoDB 连接失败: {e}")
        raise


async def close_mongodb():
    """
    关闭 MongoDB 连接
    """
    if mongodb.client:
        mongodb.client.close()
        logger.info("MongoDB 连接已关闭")


def get_client() -> AsyncIOMotorClient:
    """
    获取 MongoDB 客户端实例
    """
    if not mongodb.client:
        raise RuntimeError("MongoDB 客户端尚未初始化")
    return mongodb.client