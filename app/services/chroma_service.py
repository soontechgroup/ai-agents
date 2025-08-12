from typing import List, Dict, Any, Optional
from app.repositories.chroma_repository import ChromaRepository
from app.services.embedding_service import EmbeddingService
from app.schemas.chroma import (
    ChromaDocumentInput,
    ChromaDocumentBatch,
    ChromaQueryRequest,
    ChromaQueryResponse,
    ChromaDocument,
    ChromaAddResponse,
    ChromaCollectionInfo,
    ChromaCreateCollectionRequest,
    ChromaCreateCollectionResponse
)
from app.core.logger import logger
import uuid
from datetime import datetime


def clean_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    清理元数据，移除空值和无效值
    
    Args:
        metadata: 原始元数据
        
    Returns:
        Dict[str, Any]: 清理后的元数据
    """
    if not metadata:
        return {}
    
    cleaned = {}
    for key, value in metadata.items():
        # 跳过空值、空字典、空列表
        if value is None:
            continue
        if isinstance(value, dict) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        
        # 递归清理嵌套字典
        if isinstance(value, dict):
            cleaned_nested = clean_metadata(value)
            if cleaned_nested:  # 只添加非空的嵌套字典
                cleaned[key] = cleaned_nested
        else:
            cleaned[key] = value
    
    return cleaned


class ChromaService:
    """Chroma 服务层"""
    
    def __init__(self, chroma_repository: ChromaRepository, embedding_service: EmbeddingService):
        self.chroma_repository = chroma_repository
        self.embedding_service = embedding_service
    
    def add_documents(self, document_batch: ChromaDocumentBatch) -> ChromaAddResponse:
        """
        添加文档到 Chroma 数据库
        
        Args:
            document_batch: 批量文档数据
            
        Returns:
            ChromaAddResponse: 添加结果
        """
        try:
            documents = []
            metadatas = []
            ids = []
            
            for doc_input in document_batch.documents:
                documents.append(doc_input.content)
                
                # 处理元数据 - 先清理用户提供的元数据
                cleaned_metadata = clean_metadata(doc_input.metadata)
                
                # 获取当前时间信息
                now = datetime.now()
                
                # 添加年月信息
                time_metadata = {
                    "year_month": f"{now.year}-{now.month:02d}"  # 格式: 2024-03
                }
                
                # 合并用户元数据和时间元数据
                final_metadata = {**cleaned_metadata, **time_metadata}
                
                # 确保元数据不为空 - ChromaDB 要求至少有一个元数据字段
                if not final_metadata:
                    final_metadata = {"default": "no_metadata", **time_metadata}
                
                metadatas.append(final_metadata)
                

                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
            
            # 使用 EmbeddingService 生成嵌入向量
            logger.info(f"正在为 {len(documents)} 个文档生成嵌入向量")
            embeddings = self.embedding_service.generate_embeddings(documents)
            
            # 调用仓库层添加文档（包含嵌入向量）
            added_ids = self.chroma_repository.add_documents(
                collection_name=document_batch.collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            logger.info(f"服务层: 成功添加 {len(added_ids)} 个文档到集合 {document_batch.collection_name}")
            
            # 准备返回前5个文档的嵌入向量维度（用于测试）
            sample_embeddings = None
            if embeddings:
                # 取前5个文档的前5个维度
                sample_count = min(5, len(embeddings))
                sample_embeddings = []
                for i in range(sample_count):
                    # 每个文档取前5个维度
                    embedding_sample = embeddings[i][:5] if len(embeddings[i]) >= 5 else embeddings[i]
                    sample_embeddings.append(embedding_sample)
                logger.info(f"返回 {len(sample_embeddings)} 个文档的前5个维度用于测试")
            
            return ChromaAddResponse(
                collection_name=document_batch.collection_name,
                added_count=len(added_ids),
                document_ids=added_ids,
                sample_embeddings=sample_embeddings
            )
            
        except Exception as e:
            logger.error(f"服务层: 添加文档失败: {e}")
            raise
    
    def query_documents(self, query_request: ChromaQueryRequest) -> ChromaQueryResponse:
        """
        查询文档
        
        Args:
            query_request: 查询请求
            
        Returns:
            ChromaQueryResponse: 查询结果
        """
        try:
            # 使用 EmbeddingService 生成查询向量
            logger.info(f"正在为查询文本生成嵌入向量: {query_request.query_text[:50]}...")
            query_embedding = self.embedding_service.generate_query_embedding(query_request.query_text)
            
            # 调用仓库层查询（使用自定义向量）
            results = self.chroma_repository.query_documents(
                collection_name=query_request.collection_name,
                query_embeddings=[query_embedding],  # 使用我们生成的向量
                n_results=query_request.n_results,
                where=query_request.where,
                include=query_request.include
            )
            
            # 处理查询结果
            documents = []
            
            # ChromaDB 返回的结果结构: {'ids': [[...]], 'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
            ids = results.get('ids', [[]])[0] if results.get('ids') else []
            docs = results.get('documents', [[]])[0] if results.get('documents') else []
            metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
            distances = results.get('distances', [[]])[0] if results.get('distances') else []
            
            # 确保所有列表长度一致
            min_length = min(len(ids), len(docs))
            
            for i in range(min_length):
                doc_id = ids[i] if i < len(ids) else f"unknown_{i}"
                content = docs[i] if i < len(docs) else ""
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else None
                
                documents.append(ChromaDocument(
                    id=doc_id,
                    content=content,
                    metadata=metadata,
                    distance=distance
                ))
            
            logger.info(f"服务层: 查询集合 {query_request.collection_name} 完成，返回 {len(documents)} 个结果")
            
            return ChromaQueryResponse(
                documents=documents,
                total_results=len(documents),
                query_text=query_request.query_text,
                collection_name=query_request.collection_name
            )
            
        except Exception as e:
            logger.error(f"服务层: 查询文档失败: {e}")
            raise
    
    def get_collection_info(self, collection_name: str) -> ChromaCollectionInfo:
        """
        获取集合信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            ChromaCollectionInfo: 集合信息
        """
        try:
            info = self.chroma_repository.get_collection_info(collection_name)
            
            return ChromaCollectionInfo(
                name=info["name"],
                count=info["count"],
                metadata=info["metadata"]
            )
            
        except Exception as e:
            logger.error(f"服务层: 获取集合信息失败: {e}")
            raise
    
    def create_collection(self, request: ChromaCreateCollectionRequest) -> ChromaCreateCollectionResponse:
        """
        创建集合
        
        Args:
            request: 创建集合请求
            
        Returns:
            ChromaCreateCollectionResponse: 创建结果
        """
        try:
            created, collection_info = self.chroma_repository.create_collection(
                collection_name=request.collection_name,
                metadata=request.metadata
            )
            
            if created:
                logger.info(f"服务层: 成功创建新集合 {request.collection_name}")
            else:
                logger.info(f"服务层: 集合 {request.collection_name} 已存在")
            
            return ChromaCreateCollectionResponse(
                collection_name=request.collection_name,
                created=created,
                metadata=collection_info.get("metadata")
            )
            
        except Exception as e:
            logger.error(f"服务层: 创建集合失败: {e}")
            raise
    
    def list_collections(self) -> List[ChromaCollectionInfo]:
        """
        列出所有集合
        
        Returns:
            List[ChromaCollectionInfo]: 集合列表
        """
        try:
            collections = self.chroma_repository.list_collections()
            
            result = []
            for collection in collections:
                result.append(ChromaCollectionInfo(
                    name=collection["name"],
                    count=collection["count"],
                    metadata=collection["metadata"]
                ))
            
            logger.info(f"服务层: 获取集合列表完成，共 {len(result)} 个集合")
            return result
            
        except Exception as e:
            logger.error(f"服务层: 获取集合列表失败: {e}")
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
            result = self.chroma_repository.delete_collection(collection_name)
            logger.info(f"服务层: 删除集合 {collection_name} 成功")
            return result
            
        except Exception as e:
            logger.error(f"服务层: 删除集合失败: {e}")
            raise
    
    def delete_documents(
        self,
        collection_name: str,
        document_ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        删除文档
        
        Args:
            collection_name: 集合名称
            document_ids: 要删除的文档ID列表
            where: 元数据过滤条件
            
        Returns:
            bool: 删除是否成功
        """
        try:
            result = self.chroma_repository.delete_documents(
                collection_name=collection_name,
                ids=document_ids,
                where=where
            )
            logger.info(f"服务层: 删除集合 {collection_name} 中的文档成功")
            return result
            
        except Exception as e:
            logger.error(f"服务层: 删除文档失败: {e}")
            raise 