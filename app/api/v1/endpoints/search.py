from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.services.hybrid_search_service import HybridSearchService
from app.utils.response import ResponseUtil
from app.schemas.common_response import SuccessResponse
from app.core.logger import logger

router = APIRouter()


@router.get(
    "/hybrid",
    response_model=SuccessResponse,
    summary="混合搜索",
    description="使用语义搜索和图搜索的混合方式查找实体和关系"
)
async def hybrid_search(
    query: str = Query(..., description="搜索查询文本"),
    mode: str = Query("hybrid", description="搜索模式: semantic, graph, hybrid"),
    entity_limit: int = Query(20, description="返回实体数量限制"),
    relationship_limit: int = Query(10, description="返回关系数量限制"),
    expand_graph: bool = Query(True, description="是否进行图扩展")
):
    """
    混合搜索接口
    
    搜索模式：
    - **semantic**: 仅使用语义搜索（基于 embedding）
    - **graph**: 仅使用图搜索（Neo4j）
    - **hybrid**: 混合搜索，结合语义和图搜索（默认）
    
    返回结果包含：
    - 实体列表（包含名称、类型、描述、置信度等）
    - 关系列表（包含源、目标、类型、描述等）
    - 统计信息
    """
    try:
        search_service = HybridSearchService()
        
        results = await search_service.search(
            query=query,
            mode=mode,
            entity_limit=entity_limit,
            relationship_limit=relationship_limit,
            expand_graph=expand_graph
        )
        
        return ResponseUtil.success(
            data=results,
            message=f"搜索完成，找到 {results['statistics']['total_entities']} 个实体和 {results['statistics']['total_relationships']} 个关系"
        )
        
    except Exception as e:
        logger.error(f"混合搜索失败: {str(e)}")
        return ResponseUtil.error(message=f"搜索失败: {str(e)}")


@router.get(
    "/entities",
    response_model=SuccessResponse,
    summary="实体语义搜索",
    description="仅搜索实体，使用语义相似度"
)
async def search_entities(
    query: str = Query(..., description="搜索查询文本"),
    k: int = Query(10, description="返回结果数量")
):
    """
    实体语义搜索
    
    基于查询文本的语义相似度搜索实体
    """
    try:
        search_service = HybridSearchService()
        
        results = await search_service.search_entities(query=query, k=k)
        
        return ResponseUtil.success(
            data={"entities": results, "total": len(results)},
            message=f"找到 {len(results)} 个相关实体"
        )
        
    except Exception as e:
        logger.error(f"实体搜索失败: {str(e)}")
        return ResponseUtil.error(message=f"搜索失败: {str(e)}")


@router.get(
    "/relationships",
    response_model=SuccessResponse,
    summary="关系语义搜索",
    description="仅搜索关系，使用语义相似度"
)
async def search_relationships(
    query: str = Query(..., description="搜索查询文本"),
    k: int = Query(10, description="返回结果数量")
):
    """
    关系语义搜索
    
    基于查询文本的语义相似度搜索关系
    """
    try:
        search_service = HybridSearchService()
        
        results = await search_service.search_relationships(query=query, k=k)
        
        return ResponseUtil.success(
            data={"relationships": results, "total": len(results)},
            message=f"找到 {len(results)} 个相关关系"
        )
        
    except Exception as e:
        logger.error(f"关系搜索失败: {str(e)}")
        return ResponseUtil.error(message=f"搜索失败: {str(e)}")


@router.get(
    "/text",
    response_model=SuccessResponse,
    summary="文本块搜索",
    description="搜索相似的文本块"
)
async def search_text_chunks(
    query: str = Query(..., description="搜索查询文本"),
    k: int = Query(10, description="返回结果数量")
):
    """
    文本块语义搜索
    
    基于查询文本的语义相似度搜索文本块
    """
    try:
        search_service = HybridSearchService()
        
        results = await search_service.search_text_chunks(query=query, k=k)
        
        return ResponseUtil.success(
            data={"text_chunks": results, "total": len(results)},
            message=f"找到 {len(results)} 个相关文本块"
        )
        
    except Exception as e:
        logger.error(f"文本搜索失败: {str(e)}")
        return ResponseUtil.error(message=f"搜索失败: {str(e)}")