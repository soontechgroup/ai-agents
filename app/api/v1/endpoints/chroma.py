from fastapi import APIRouter, Depends, HTTPException, status
from app.services.chroma_service import ChromaService
from app.dependencies.services import get_chroma_service
from app.schemas.chroma import (
    ChromaDocumentBatch,
    ChromaQueryRequest,
    ChromaQueryResponse,
    ChromaAddResponse,
    ChromaCollectionInfo
)
from app.utils.response import ResponseUtil
from app.schemas.common import SuccessResponse, ErrorResponse
from typing import List, Dict, Any, Optional

router = APIRouter()


@router.post(
    "/documents",
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
    
    注意：文档ID将由系统自动生成，确保唯一性
    """
    try:
        result = chroma_service.add_documents(document_batch)
        return ResponseUtil.success(
            data=result,
            message=f"成功添加 {result.added_count} 个文档到集合 {result.collection_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加文档失败: {str(e)}"
        )


@router.post(
    "/query",
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
    try:
        result = chroma_service.query_documents(query_request)
        return ResponseUtil.success(
            data=result,
            message=f"查询完成，找到 {result.total_results} 个相关文档"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询文档失败: {str(e)}"
        )


@router.get(
    "/collections",
    response_model=SuccessResponse[List[ChromaCollectionInfo]],
    summary="获取所有集合信息",
    description="列出所有 Chroma 集合及其基本信息"
)
async def list_collections(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    获取所有集合信息
    
    返回所有集合的名称、文档数量和元数据
    """
    try:
        collections = chroma_service.list_collections()
        return ResponseUtil.success(
            data=collections,
            message=f"获取集合列表成功，共 {len(collections)} 个集合"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取集合列表失败: {str(e)}"
        )


@router.get(
    "/collections/{collection_name}",
    response_model=SuccessResponse[ChromaCollectionInfo],
    summary="获取指定集合信息",
    description="获取指定集合的详细信息，包括文档数量和元数据"
)
async def get_collection_info(
    collection_name: str,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    获取指定集合信息
    
    - **collection_name**: 集合名称
    """
    try:
        collection_info = chroma_service.get_collection_info(collection_name)
        return ResponseUtil.success(
            data=collection_info,
            message=f"获取集合 {collection_name} 信息成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取集合信息失败: {str(e)}"
        )


@router.delete(
    "/collections/{collection_name}",
    response_model=SuccessResponse[Dict[str, str]],
    summary="删除集合",
    description="删除指定的 Chroma 集合及其所有文档"
)
async def delete_collection(
    collection_name: str,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    删除集合
    
    - **collection_name**: 要删除的集合名称
    
    ⚠️ 警告：此操作会删除集合中的所有文档，且不可恢复
    """
    try:
        success = chroma_service.delete_collection(collection_name)
        if success:
            return ResponseUtil.success(
                data={"collection_name": collection_name},
                message=f"成功删除集合 {collection_name}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除集合失败"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除集合失败: {str(e)}"
        )


@router.delete(
    "/collections/{collection_name}/documents",
    response_model=SuccessResponse[Dict[str, str]],
    summary="删除文档",
    description="根据文档ID或元数据过滤条件删除文档"
)
async def delete_documents(
    collection_name: str,
    document_ids: Optional[List[str]] = None,
    where: Optional[Dict[str, Any]] = None,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """
    删除文档
    
    - **collection_name**: 集合名称
    - **document_ids**: 可选，要删除的文档ID列表
    - **where**: 可选，元数据过滤条件
    
    注意：document_ids 和 where 至少需要提供一个
    """
    if not document_ids and not where:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供 document_ids 或 where 过滤条件"
        )
    
    try:
        success = chroma_service.delete_documents(
            collection_name=collection_name,
            document_ids=document_ids,
            where=where
        )
        
        if success:
            return ResponseUtil.success(
                data={"collection_name": collection_name},
                message=f"成功删除集合 {collection_name} 中的文档"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除文档失败"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        ) 