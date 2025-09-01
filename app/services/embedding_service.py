import os
from typing import List
from langchain_openai import OpenAIEmbeddings
import openai
from app.core.logger import logger


class EmbeddingService:
    """文本嵌入向量服务"""
    
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
            
            logger.info("✅ EmbeddingService 初始化完成")
            
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