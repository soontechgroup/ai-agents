import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
import uuid
import os
from app.core.logger import logger


class ChromaRepository:
    """Chroma 数据库访问层"""
    
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """
        初始化 Chroma 客户端
        
        Args:
            persist_directory: 持久化存储目录
        """
        self.persist_directory = persist_directory
        
        # 确保持久化目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        logger.info(f"✅ ChromaDB 客户端初始化完成，存储路径: {persist_directory}")
    
    def get_or_create_collection(self, collection_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        获取或创建集合
        
        Args:
            collection_name: 集合名称
            metadata: 集合元数据
            
        Returns:
            Collection: Chroma 集合对象
        """
        try:
            # 确保集合元数据不为空 - ChromaDB 要求非空元数据
            collection_metadata = metadata or {"created_by": "ai_agents_system"}
            
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=collection_metadata
            )
            logger.debug(f"获取/创建集合成功: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"获取/创建集合失败 {collection_name}: {e}")
            raise
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        """
        向集合中添加文档
        
        Args:
            collection_name: 集合名称
            documents: 文档内容列表
            metadatas: 文档元数据列表
            ids: 文档ID列表，如果不提供则自动生成
            embeddings: 嵌入向量列表，如果不提供则使用 Chroma 默认向量化
            
        Returns:
            List[str]: 添加的文档ID列表
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # 如果没有提供ID，则自动生成
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # 确保ID数量与文档数量匹配
            if len(ids) != len(documents):
                raise ValueError("文档ID数量与文档数量不匹配")
            
            # 如果没有提供元数据，创建默认元数据
            if metadatas is None:
                metadatas = [{"added_at": str(uuid.uuid4())} for _ in documents]
            
            # 确保每个文档的元数据都不为空
            for i, metadata in enumerate(metadatas):
                if not metadata:
                    metadatas[i] = {"default": "empty_metadata"}
                logger.debug(f"文档 {i} 元数据: {metadatas[i]}")
            
            # 添加文档到集合
            add_params = {
                "documents": documents,
                "metadatas": metadatas,
                "ids": ids
            }
            
            # 如果提供了嵌入向量，则使用自定义向量
            if embeddings is not None:
                add_params["embeddings"] = embeddings
                logger.debug(f"使用自定义嵌入向量添加 {len(embeddings)} 个文档")
            else:
                logger.debug("使用 Chroma 默认嵌入向量")
            
            collection.add(**add_params)
            
            logger.info(f"成功添加 {len(documents)} 个文档到集合 {collection_name}")
            return ids
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise
    
    def query_documents(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: List[str] = None
    ) -> Dict[str, Any]:
        """
        查询文档
        
        Args:
            collection_name: 集合名称
            query_texts: 查询文本列表
            n_results: 返回结果数量
            where: 元数据过滤条件
            include: 包含的字段列表
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            if include is None:
                include = ["documents", "metadatas", "distances"]
            
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                include=include
            )
            
            logger.debug(f"查询集合 {collection_name} 完成，返回 {len(results.get('ids', [[]]))} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"查询文档失败: {e}")
            raise
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Dict[str, Any]: 集合信息
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            count = collection.count()
            metadata = collection.metadata
            
            return {
                "name": collection_name,
                "count": count,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            raise
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        列出所有集合
        
        Returns:
            List[Dict[str, Any]]: 集合列表
        """
        try:
            collections = self.client.list_collections()
            result = []
            
            for collection in collections:
                result.append({
                    "name": collection.name,
                    "count": collection.count(),
                    "metadata": collection.metadata
                })
            
            logger.debug(f"获取集合列表完成，共 {len(result)} 个集合")
            return result
            
        except Exception as e:
            logger.error(f"获取集合列表失败: {e}")
            raise
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"删除集合 {collection_name} 成功")
            return True
            
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            raise
    
    def delete_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        删除文档
        
        Args:
            collection_name: 集合名称
            ids: 要删除的文档ID列表
            where: 元数据过滤条件
            
        Returns:
            bool: 删除是否成功
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            collection.delete(
                ids=ids,
                where=where
            )
            
            logger.info(f"删除集合 {collection_name} 中的文档成功")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise 