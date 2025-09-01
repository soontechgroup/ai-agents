from fastapi import APIRouter, Depends, HTTPException, status
from app.services.chroma_service import ChromaService
from app.dependencies.services import get_chroma_service
from app.schemas.chroma import (
    ChromaDocumentBatch,
    ChromaQueryRequest,
    ChromaQueryResponse,
    ChromaAddResponse,
    ChromaCollectionInfo,
    ChromaListCollectionsRequest,
    ChromaGetCollectionRequest,
    ChromaDeleteCollectionRequest,
    ChromaDeleteDocumentsRequest,
    ChromaCreateCollectionRequest,
    ChromaCreateCollectionResponse
)
from app.utils.response import ResponseUtil
from app.schemas.common_response import SuccessResponse, ErrorResponse
from typing import List, Dict, Any, Optional

router = APIRouter()


@router.post(
    "/document/add",
    response_model=SuccessResponse[ChromaAddResponse],
    summary="添加文档到 Chroma 数据库",
    description="批量添加文档到指定的 Chroma 集合中，支持自定义元数据和文档ID"
)
async def add_documents(
    document_batch: ChromaDocumentBatch,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    添加文档到 Chroma 数据库
    
    - **documents**: 文档列表，每个文档包含内容和可选的元数据
    - **collection_name**: 目标集合名称，如果不存在会自动创建
    
    注意：
    - 文档ID将由系统自动生成UUID，确保唯一性
    - 使用 OpenAI text-embedding-3-small 模型进行向量化
    - 返回结果包含前5个文档的前5个维度用于测试验证
    """
    result = chroma_service.add_documents(document_batch)
    return ResponseUtil.success(
        data=result,
        message=f"成功添加 {result.added_count} 个文档到集合 {result.collection_name}"
    )


@router.post(
    "/document/query",
    response_model=SuccessResponse[ChromaQueryResponse],
    summary="查询 Chroma 数据库",
    description="根据文本内容查询相似的文档，支持元数据过滤和结果数量限制"
)
async def query_documents(
    query_request: ChromaQueryRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    查询 Chroma 数据库
    
    - **query_text**: 查询文本
    - **collection_name**: 目标集合名称
    - **n_results**: 返回结果数量 (1-100)
    - **where**: 可选的元数据过滤条件
    - **include**: 返回字段列表，默认包含文档、元数据和距离
    """
    result = chroma_service.query_documents(query_request)
    return ResponseUtil.success(
        data=result,
        message=f"查询完成，找到 {result.total_results} 个相关文档"
    )


@router.post(
    "/collection/create",
    response_model=SuccessResponse[ChromaCreateCollectionResponse],
    summary="创建集合",
    description="创建一个新的 Chroma 集合，支持自定义元数据"
)
async def create_collection(
    request: ChromaCreateCollectionRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    创建集合
    
    - **collection_name**: 集合名称
    - **metadata**: 可选的集合元数据
    
    如果集合已存在，会返回已存在的集合信息
    """
    result = chroma_service.create_collection(request)
    message = f"成功创建集合 {result.collection_name}" if result.created else f"集合 {result.collection_name} 已存在"
    return ResponseUtil.success(
        data=result,
        message=message
    )


@router.post(
    "/collection/list",
    response_model=SuccessResponse[List[ChromaCollectionInfo]],
    summary="获取所有集合信息",
    description="列出所有 Chroma 集合及其基本信息"
)
async def list_collections(
    request: ChromaListCollectionsRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    获取所有集合信息
    
    返回所有集合的名称、文档数量和元数据
    """
    collections = chroma_service.list_collections()
    return ResponseUtil.success(
        data=collections,
        message=f"获取集合列表成功，共 {len(collections)} 个集合"
    )


@router.post(
    "/collection/info",
    response_model=SuccessResponse[ChromaCollectionInfo],
    summary="获取指定集合信息",
    description="获取指定集合的详细信息，包括文档数量和元数据"
)
async def get_collection_info(
    request: ChromaGetCollectionRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    获取指定集合信息
    
    - **collection_name**: 集合名称
    """
    collection_info = chroma_service.get_collection_info(request.collection_name)
    return ResponseUtil.success(
        data=collection_info,
        message=f"获取集合 {request.collection_name} 信息成功"
    )


@router.post(
    "/collection/delete",
    response_model=SuccessResponse[Dict[str, str]],
    summary="删除集合",
    description="删除指定的 Chroma 集合及其所有文档"
)
async def delete_collection(
    request: ChromaDeleteCollectionRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    删除集合
    
    - **collection_name**: 要删除的集合名称
    
    ⚠️ 警告：此操作会删除集合中的所有文档，且不可恢复
    """
    success = chroma_service.delete_collection(request.collection_name)
    if success:
        return ResponseUtil.success(
            data={"collection_name": request.collection_name},
            message=f"成功删除集合 {request.collection_name}"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除集合失败"
        )


@router.post(
    "/document/delete",
    response_model=SuccessResponse[Dict[str, str]],
    summary="删除文档",
    description="根据文档ID或元数据过滤条件删除文档"
)
async def delete_documents(
    request: ChromaDeleteDocumentsRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    删除文档
    
    - **collection_name**: 集合名称
    - **document_ids**: 可选，要删除的文档ID列表
    - **where**: 可选，元数据过滤条件
    
    注意：document_ids 和 where 至少需要提供一个
    """
    if not request.document_ids and not request.where:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供 document_ids 或 where 过滤条件"
        )
    
    success = chroma_service.delete_documents(
        collection_name=request.collection_name,
        document_ids=request.document_ids,
        where=request.where
    )
    
    if success:
        return ResponseUtil.success(
            data={"collection_name": request.collection_name},
            message=f"成功删除集合 {request.collection_name} 中的文档"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文档失败"
        ) 