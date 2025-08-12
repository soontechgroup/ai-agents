from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChromaDocumentInput(BaseModel):
    """Chroma 文档输入模型"""
    content: str = Field(..., description="文档内容")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="文档元数据")
    # document_id 由系统自动生成，用户无需提供


class ChromaDocumentBatch(BaseModel):
    """Chroma 批量文档输入模型"""
    documents: List[ChromaDocumentInput] = Field(..., description="文档列表")
    collection_name: str = Field(..., description="集合名称")


class ChromaQueryRequest(BaseModel):
    """Chroma 查询请求模型"""
    query_text: str = Field(..., description="查询文本")
    collection_name: str = Field(..., description="集合名称")
    n_results: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    where: Optional[Dict[str, Any]] = Field(default=None, description="元数据过滤条件")
    include: List[str] = Field(default=["documents", "metadatas", "distances"], description="包含的字段")


class ChromaDocument(BaseModel):
    """Chroma 文档响应模型"""
    id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="文档元数据")
    distance: Optional[float] = Field(default=None, description="相似度距离")


class ChromaQueryResponse(BaseModel):
    """Chroma 查询响应模型"""
    documents: List[ChromaDocument] = Field(..., description="匹配的文档列表")
    total_results: int = Field(..., description="总结果数")
    query_text: str = Field(..., description="查询文本")
    collection_name: str = Field(..., description="集合名称")


class ChromaCollectionInfo(BaseModel):
    """Chroma 集合信息模型"""
    name: str = Field(..., description="集合名称")
    count: int = Field(..., description="文档数量")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="集合元数据")


class ChromaAddResponse(BaseModel):
    """Chroma 添加文档响应模型"""
    collection_name: str = Field(..., description="集合名称")
    added_count: int = Field(..., description="添加的文档数量")
    document_ids: List[str] = Field(..., description="添加的文档ID列表")
    sample_embeddings: Optional[List[List[float]]] = Field(default=None, description="前5个文档的嵌入向量（用于测试）")


class ChromaListCollectionsRequest(BaseModel):
    """Chroma 列出集合请求模型"""
    pass  # 暂时不需要参数，但保持接口一致性


class ChromaGetCollectionRequest(BaseModel):
    """Chroma 获取集合信息请求模型"""
    collection_name: str = Field(..., description="集合名称")


class ChromaDeleteCollectionRequest(BaseModel):
    """Chroma 删除集合请求模型"""
    collection_name: str = Field(..., description="集合名称")


class ChromaDeleteDocumentsRequest(BaseModel):
    """Chroma 删除文档请求模型"""
    collection_name: str = Field(..., description="集合名称")
    document_ids: Optional[List[str]] = Field(default=None, description="要删除的文档ID列表")
    where: Optional[Dict[str, Any]] = Field(default=None, description="元数据过滤条件")


class ChromaCreateCollectionRequest(BaseModel):
    """Chroma 创建集合请求模型"""
    collection_name: str = Field(..., description="集合名称")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="集合元数据")


class ChromaCreateCollectionResponse(BaseModel):
    """Chroma 创建集合响应模型"""
    collection_name: str = Field(..., description="集合名称")
    created: bool = Field(..., description="是否新创建（false表示集合已存在）")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="集合元数据") 