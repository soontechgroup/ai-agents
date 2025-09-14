import os
from typing import List, Dict, Any, Optional
import json
import uuid
import hashlib
from langchain_openai import OpenAIEmbeddings
import openai
from app.repositories.chroma_repository import ChromaRepository
from app.core.logger import logger


class EmbeddingService:
    """增强的文本嵌入向量服务，支持实体、关系和文本块的语义表示"""
    
    def __init__(self):
        """初始化 Embedding 服务，复用现有的 OpenAI 配置"""
        try:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            # 验证 OpenAI API 密钥
            self._validate_openai_api_key()
            
            # 初始化 OpenAI Embeddings 客户端
            # 使用 text-embedding-3-small 模型的默认维度 (1536)
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                model="text-embedding-3-small",  # 默认维度 1536，更好的效果
                timeout=30
            )
            
            # 初始化 ChromaDB 仓储
            self.chroma_repo = ChromaRepository()
            
            # 初始化缓存
            self.cache = {}
            
            # 初始化 ChromaDB 集合
            self._init_collections()
            
            logger.info("✅ EmbeddingService 初始化完成（增强版）")
            
        except openai.AuthenticationError:
            raise ValueError("Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable.")
        except openai.RateLimitError:
            raise ValueError("OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise ValueError(f"OpenAI API error during initialization: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to initialize EmbeddingService: {str(e)}")
    
    def _validate_openai_api_key(self):
        """验证 OpenAI API 密钥是否有效"""
        try:
            # 创建临时客户端进行验证
            client = openai.OpenAI(api_key=self.openai_api_key)
            # 尝试获取模型列表来验证密钥
            client.models.list()
            logger.debug("OpenAI API 密钥验证成功")
        except Exception as e:
            logger.error(f"OpenAI API 密钥验证失败: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        try:
            if not texts:
                return []
            
            logger.debug(f"正在为 {len(texts)} 个文档生成嵌入向量")
            
            # 使用 Langchain 的 OpenAIEmbeddings 生成向量
            embeddings = self.embeddings.embed_documents(texts)
            
            logger.info(f"成功生成 {len(embeddings)} 个嵌入向量")
            return embeddings
            
        except openai.AuthenticationError:
            logger.error("OpenAI API 认证失败")
            raise ValueError("OpenAI API authentication failed")
        except openai.RateLimitError:
            logger.error("OpenAI API 速率限制")
            raise ValueError("OpenAI API rate limit exceeded")
        except openai.APIError as e:
            logger.error(f"OpenAI API 错误: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            raise ValueError(f"Failed to generate embeddings: {str(e)}")
    
    def generate_query_embedding(self, query_text: str) -> List[float]:
        """
        为查询文本生成嵌入向量
        
        Args:
            query_text: 查询文本
            
        Returns:
            List[float]: 查询向量
        """
        try:
            logger.debug(f"正在为查询文本生成嵌入向量: {query_text[:50]}...")
            
            # 使用 Langchain 的 OpenAIEmbeddings 生成查询向量
            embedding = self.embeddings.embed_query(query_text)
            
            logger.debug("查询嵌入向量生成成功")
            return embedding
            
        except Exception as e:
            logger.error(f"生成查询嵌入向量失败: {e}")
            raise ValueError(f"Failed to generate query embedding: {str(e)}")
    
    def _init_collections(self):
        """初始化 ChromaDB 集合"""
        self.chroma_repo.get_or_create_collection(
            collection_name="entity_embeddings",
            metadata={"description": "Entity semantic embeddings"}
        )
        
        self.chroma_repo.get_or_create_collection(
            collection_name="relationship_embeddings",
            metadata={"description": "Relationship semantic embeddings"}
        )
        
        self.chroma_repo.get_or_create_collection(
            collection_name="text_chunk_embeddings",
            metadata={"description": "Text chunk embeddings"}
        )
        
        logger.info("ChromaDB collections initialized")
    
    async def embed_entity(self, entity: Dict[str, Any], digital_human_id: int) -> Dict[str, Any]:
        """生成实体的 embedding 并存储到 ChromaDB"""
        text = self._build_entity_text(entity)
        
        # 缓存键包含数字人ID
        cache_key = self._get_cache_key(f"{digital_human_id}:{text}")
        if cache_key in self.cache:
            logger.debug(f"Using cached embedding for entity: {entity.get('name')} (DH: {digital_human_id})")
            return self.cache[cache_key]
        
        try:
            embedding = self.embeddings.embed_documents([text])[0]
            
            doc_id = str(uuid.uuid4())
            
            metadata = {
                "digital_human_id": str(digital_human_id),  # 添加数字人ID
                "entity_name": entity.get("name", ""),
                "entity_types": json.dumps(entity.get("types", [])),
                "description": entity.get("description", ""),
                "neo4j_id": entity.get("id", ""),
                "confidence": str(entity.get("confidence", 0.5))
            }
            
            if entity.get("properties"):
                metadata["properties"] = json.dumps(entity["properties"])
            
            self.chroma_repo.add_documents(
                collection_name="entity_embeddings",
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id],
                embeddings=[embedding]
            )
            
            result = {
                "embedding_id": doc_id,
                "vector": embedding,
                "text": text
            }
            
            self.cache[cache_key] = result
            
            logger.info(f"Created embedding for entity: {entity.get('name')} (DH: {digital_human_id})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to embed entity {entity.get('name')}: {str(e)}")
            raise
    
    async def embed_relationship(self, relationship: Dict[str, Any], digital_human_id: int) -> Dict[str, Any]:
        """生成关系的 embedding 并存储到 ChromaDB"""
        text = self._build_relationship_text(relationship)
        
        cache_key = self._get_cache_key(f"{digital_human_id}:{text}")
        if cache_key in self.cache:
            logger.debug(f"Using cached embedding for relationship (DH: {digital_human_id})")
            return self.cache[cache_key]
        
        try:
            embedding = self.embeddings.embed_documents([text])[0]
            
            doc_id = str(uuid.uuid4())
            
            metadata = {
                "digital_human_id": str(digital_human_id),  # 添加数字人ID
                "source": relationship.get("source", ""),
                "target": relationship.get("target", ""),
                "relation_types": json.dumps(relationship.get("types", [])),
                "description": relationship.get("description", ""),
                "confidence": str(relationship.get("confidence", 0.5)),
                "strength": str(relationship.get("strength", 0.5))
            }
            
            if relationship.get("properties"):
                metadata["properties"] = json.dumps(relationship["properties"])
            
            self.chroma_repo.add_documents(
                collection_name="relationship_embeddings",
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id],
                embeddings=[embedding]
            )
            
            result = {
                "embedding_id": doc_id,
                "vector": embedding,
                "text": text
            }
            
            self.cache[cache_key] = result
            
            logger.info(f"Created embedding for relationship: {relationship.get('source')} -> {relationship.get('target')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to embed relationship: {str(e)}")
            raise
    
    async def embed_text_chunk(self, chunk: str, digital_human_id: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成文本块的 embedding 并存储到 ChromaDB"""
        cache_key = self._get_cache_key(f"{digital_human_id}:{chunk}")
        if cache_key in self.cache:
            logger.debug(f"Using cached embedding for text chunk (DH: {digital_human_id})")
            return self.cache[cache_key]
        
        try:
            embedding = self.embeddings.embed_documents([chunk])[0]
            
            doc_id = str(uuid.uuid4())
            
            chunk_metadata = metadata or {}
            chunk_metadata["digital_human_id"] = str(digital_human_id)
            chunk_metadata["chunk_length"] = str(len(chunk))
            
            self.chroma_repo.add_documents(
                collection_name="text_chunk_embeddings",
                documents=[chunk],
                metadatas=[chunk_metadata],
                ids=[doc_id],
                embeddings=[embedding]
            )
            
            result = {
                "embedding_id": doc_id,
                "vector": embedding,
                "text": chunk
            }
            
            self.cache[cache_key] = result
            
            logger.info(f"Created embedding for text chunk (length: {len(chunk)}, DH: {digital_human_id})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to embed text chunk: {str(e)}")
            raise
    
    async def batch_embed_entities(self, entities: List[Dict[str, Any]], digital_human_id: int) -> List[Dict[str, Any]]:
        """批量生成实体的 embeddings"""
        results = []
        texts = [self._build_entity_text(entity) for entity in entities]
        
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(f"{digital_human_id}:{text}")
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                results.append(None)
        
        if uncached_texts:
            try:
                embeddings = self.embeddings.embed_documents(uncached_texts)
                
                doc_ids = []
                metadatas = []
                
                for idx, embedding_idx in enumerate(uncached_indices):
                    entity = entities[embedding_idx]
                    doc_id = str(uuid.uuid4())
                    doc_ids.append(doc_id)

                    metadata = {
                        "digital_human_id": str(digital_human_id),
                        "entity_name": entity.get("name", ""),
                        "entity_types": json.dumps(entity.get("types", [])),
                        "description": entity.get("description", ""),
                        "neo4j_id": entity.get("id", ""),
                        "confidence": str(entity.get("confidence", 0.5))
                    }

                    if entity.get("properties"):
                        metadata["properties"] = json.dumps(entity["properties"])

                    metadatas.append(metadata)

                    # embeddings 是列表的列表，第一个维度是文档，第二个维度是向量
                    embedding_vector = embeddings[idx] if len(embeddings) > idx else embeddings[0] if embeddings else []

                    result = {
                        "embedding_id": doc_id,
                        "vector": embedding_vector,
                        "text": uncached_texts[idx]
                    }

                    cache_key = self._get_cache_key(f"{digital_human_id}:{uncached_texts[idx]}")
                    self.cache[cache_key] = result
                    results[embedding_idx] = result
                
                self.chroma_repo.add_documents(
                    collection_name="entity_embeddings",
                    documents=uncached_texts,
                    metadatas=metadatas,
                    ids=doc_ids,
                    embeddings=embeddings
                )
                
                logger.info(f"Batch created {len(uncached_texts)} entity embeddings (DH: {digital_human_id})")
                
            except Exception as e:
                logger.error(f"Failed to batch embed entities: {str(e)}")
                raise
        
        return results
    
    async def semantic_search(
        self,
        query: str,
        collection: str,
        digital_human_id: int,
        k: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            if where is None:
                where = {}
            where["digital_human_id"] = str(digital_human_id)
            
            results = self.chroma_repo.query_with_embedding(
                collection_name=collection,
                query_embedding=query_embedding,
                n_results=k,
                where=where
            )
            
            processed_results = []
            if results and results.get("documents"):
                for i in range(len(results["documents"][0])):
                    processed_results.append({
                        "document": results["documents"][0][i] if results["documents"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                        "id": results["ids"][0][i] if results["ids"] else None
                    })
            
            logger.info(f"Semantic search in {collection} for DH {digital_human_id} returned {len(processed_results)} results")
            return processed_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            raise
    
    def _build_entity_text(self, entity: Dict[str, Any]) -> str:
        """构建实体的文本表示"""
        components = []
        
        if entity.get("name"):
            components.append(f"Entity: {entity['name']}")
        
        if entity.get("types"):
            types_str = ", ".join(entity["types"]) if isinstance(entity["types"], list) else entity["types"]
            components.append(f"Type: {types_str}")
        elif entity.get("type"):
            components.append(f"Type: {entity['type']}")
        
        if entity.get("description"):
            components.append(f"Description: {entity['description']}")
        
        if entity.get("properties") and isinstance(entity["properties"], dict):
            props_str = ", ".join([f"{k}: {v}" for k, v in entity["properties"].items()])
            components.append(f"Properties: {props_str}")
        
        return " | ".join(components)
    
    def _build_relationship_text(self, relationship: Dict[str, Any]) -> str:
        """构建关系的文本表示"""
        components = []
        
        source = relationship.get("source", "?")
        target = relationship.get("target", "?")
        
        if relationship.get("types"):
            types_str = ", ".join(relationship["types"]) if isinstance(relationship["types"], list) else relationship["types"]
        elif relationship.get("relation_type"):
            types_str = relationship["relation_type"]
        else:
            types_str = "RELATED_TO"
        
        components.append(f"Relationship: {source} --[{types_str}]--> {target}")
        
        if relationship.get("description"):
            components.append(f"Description: {relationship['description']}")
        
        if relationship.get("strength"):
            components.append(f"Strength: {relationship['strength']}")
        
        if relationship.get("properties") and isinstance(relationship["properties"], dict):
            props_str = ", ".join([f"{k}: {v}" for k, v in relationship["properties"].items()])
            components.append(f"Properties: {props_str}")
        
        return " | ".join(components)
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("Embedding cache cleared") 