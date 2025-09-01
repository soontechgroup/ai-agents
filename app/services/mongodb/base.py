"""
MongoDB 服务基类
提供依赖注入支持和通用功能
"""
from typing import Optional, Type, TypeVar, Generic
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from beanie import Document
from loguru import logger


T = TypeVar('T', bound=Document)


class MongoDBServiceBase(Generic[T]):
    """
    MongoDB 服务基类
    
    这个基类展示了如何在保持 Beanie 便利性的同时，
    也支持依赖注入模式和原始 MongoDB 操作
    """
    
    def __init__(
        self, 
        document_class: Type[T],
        client: Optional[AsyncIOMotorClient] = None,
        database_name: Optional[str] = None
    ):
        """
        初始化服务
        
        Args:
            document_class: Beanie 文档类
            client: MongoDB 客户端（用于所有 MongoDB 操作）
            database_name: 数据库名称（可选，默认从环境变量获取）
        """
        self.document_class = document_class
        self.client = client
        self.database_name = database_name
        
    @property
    def db(self) -> Optional[AsyncIOMotorDatabase]:
        """获取数据库实例"""
        if self.client and self.database_name:
            return self.client[self.database_name]
        return None
        
    async def create(self, **kwargs) -> T:
        """创建新文档"""
        doc = self.document_class(**kwargs)
        await doc.insert()
        logger.info(f"创建 {self.document_class.__name__}: {doc.id}")
        return doc
    
    async def find_by_id(self, doc_id: str) -> Optional[T]:
        """根据 ID 查找文档"""
        return await self.document_class.get(doc_id)
    
    async def find_one(self, **filters) -> Optional[T]:
        """查找单个文档"""
        return await self.document_class.find_one(filters)
    
    async def find_many(
        self, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> list[T]:
        """查找多个文档"""
        query = self.document_class.find(filters)
        return await query.skip(skip).limit(limit).to_list()
    
    async def update(self, doc_id: str, **updates) -> Optional[T]:
        """更新文档"""
        doc = await self.find_by_id(doc_id)
        if doc:
            for key, value in updates.items():
                setattr(doc, key, value)
            await doc.save()
            logger.info(f"更新 {self.document_class.__name__}: {doc_id}")
        return doc
    
    async def delete(self, doc_id: str) -> bool:
        """删除文档"""
        doc = await self.find_by_id(doc_id)
        if doc:
            await doc.delete()
            logger.info(f"删除 {self.document_class.__name__}: {doc_id}")
            return True
        return False
    
    async def count(self, **filters) -> int:
        """统计文档数量"""
        if filters:
            return await self.document_class.find(filters).count()
        return await self.document_class.find_all().count()
    
    async def aggregate(self, pipeline: list) -> list:
        """
        执行聚合管道（需要原始 MongoDB 操作）
        """
        if not self.client or not self.database_name:
            raise RuntimeError("聚合操作需要 MongoDB 客户端和数据库名")
        
        db = self.client[self.database_name]
        collection_name = self.document_class.Settings.name
        results = []
        async for doc in db[collection_name].aggregate(pipeline):
            results.append(doc)
        return results
    
    async def bulk_insert(self, documents: list[dict]) -> list[T]:
        """批量插入文档"""
        docs = [self.document_class(**doc) for doc in documents]
        await self.document_class.insert_many(docs)
        logger.info(f"批量插入 {len(docs)} 个 {self.document_class.__name__}")
        return docs
    
    async def create_index(self, keys: list, **options):
        """
        创建索引（需要原始 MongoDB 操作）
        """
        if not self.client or not self.database_name:
            raise RuntimeError("创建索引需要 MongoDB 客户端和数据库名")
        
        db = self.client[self.database_name]
        collection_name = self.document_class.Settings.name
        return await db[collection_name].create_index(keys, **options)

