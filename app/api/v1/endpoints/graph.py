"""Neo4j 图数据库 API 端点"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.models import User
from app.guards.auth import get_current_user
from app.schemas.common_response import SuccessResponse
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_repository
from app.repositories.graph import GraphRepository
from app.services.graph_service import GraphService

router = APIRouter(tags=["Graph Database"])


# ==================== 请求模型 ====================

class CreateNodeRequest(BaseModel):
    label: str
    properties: Dict[str, Any]


class CreateRelationshipRequest(BaseModel):
    from_node_id: int
    to_node_id: int
    rel_type: str
    properties: Dict[str, Any] = {}


class UpdateNodeRequest(BaseModel):
    properties: Dict[str, Any]


class SearchRequest(BaseModel):
    label: str
    keyword: str
    properties: List[str]


class FindNodesRequest(BaseModel):
    label: Optional[str] = None
    limit: int = 100


# ==================== 基础 CRUD 操作 ====================

@router.post("/nodes", response_model=SuccessResponse, summary="创建节点")
async def create_node(
    request: CreateNodeRequest,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        node = graph.nodes.create(request.label, request.properties)
        return ResponseUtil.success(data=node, message="节点创建成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}", response_model=SuccessResponse, summary="获取节点")
async def get_node(
    node_id: int,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        node = graph.nodes.find_by_id(node_id)
        if not node:
            return ResponseUtil.error(message="节点不存在")
        return ResponseUtil.success(data=node)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nodes/{node_id}", response_model=SuccessResponse, summary="更新节点")
async def update_node(
    node_id: int,
    request: UpdateNodeRequest,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        node = graph.nodes.update(node_id, request.properties)
        if not node:
            return ResponseUtil.error(message="节点不存在或更新失败")
        return ResponseUtil.success(data=node, message="节点更新成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nodes/{node_id}", response_model=SuccessResponse, summary="删除节点")
async def delete_node(
    node_id: int,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        success = graph.delete_node_cascade(node_id)
        if not success:
            return ResponseUtil.error(message="节点不存在或删除失败")
        return ResponseUtil.success(message="节点删除成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes", response_model=SuccessResponse, summary="查找节点")
async def find_nodes(
    label: Optional[str] = None,
    limit: int = 100,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        nodes = graph.nodes.find_all(label, limit)
        return ResponseUtil.success(
            data={"nodes": nodes, "count": len(nodes)},
            message="查询成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SuccessResponse, summary="搜索节点")
async def search_nodes(
    request: SearchRequest,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        nodes = graph.nodes.search(
            request.label,
            request.keyword,
            request.properties
        )
        return ResponseUtil.success(
            data={"nodes": nodes, "count": len(nodes)},
            message=f"找到 {len(nodes)} 个匹配节点"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 关系操作 ====================

@router.post("/relationships", response_model=SuccessResponse, summary="创建关系")
async def create_relationship(
    request: CreateRelationshipRequest,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        relationship = graph.relationships.create(
            request.from_node_id,
            request.to_node_id,
            request.rel_type,
            request.properties
        )
        if not relationship:
            return ResponseUtil.error(message="创建关系失败，请检查节点是否存在")
        return ResponseUtil.success(data=relationship, message="关系创建成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}/connections", response_model=SuccessResponse, summary="获取节点连接")
async def get_node_connections(
    node_id: int,
    rel_type: Optional[str] = None,
    direction: str = "both",
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        node_with_connections = graph.find_node_with_connections(
            node_id, rel_type, direction
        )
        if not node_with_connections:
            return ResponseUtil.error(message="节点不存在")
        return ResponseUtil.success(data=node_with_connections)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 高级操作 ====================

@router.post("/batch/nodes", response_model=SuccessResponse, summary="批量创建节点")
async def create_nodes_batch(
    nodes_data: List[Dict[str, Any]],
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        created_nodes = graph.create_nodes_batch(nodes_data)
        return ResponseUtil.success(
            data={"nodes": created_nodes, "count": len(created_nodes)},
            message=f"成功创建 {len(created_nodes)} 个节点"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/relationships", response_model=SuccessResponse, summary="批量创建关系")
async def create_relationships_batch(
    relationships_data: List[Dict[str, Any]],
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        created_relationships = graph.create_relationships_batch(relationships_data)
        return ResponseUtil.success(
            data={"relationships": created_relationships, "count": len(created_relationships)},
            message=f"成功创建 {len(created_relationships)} 个关系"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clone/{node_id}", response_model=SuccessResponse, summary="克隆节点")
async def clone_node(
    node_id: int,
    new_properties: Optional[Dict[str, Any]] = None,
    clone_relationships: bool = False,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        cloned_node = graph.clone_node(node_id, new_properties, clone_relationships)
        if not cloned_node:
            return ResponseUtil.error(message="节点不存在或克隆失败")
        return ResponseUtil.success(data=cloned_node, message="节点克隆成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=SuccessResponse, summary="获取统计信息")
async def get_statistics(
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        stats = graph.get_statistics()
        return ResponseUtil.success(data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 业务相关端点 ====================

@router.post("/sync/user", response_model=SuccessResponse, summary="同步用户到图数据库")
async def sync_user_to_graph(
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        # 使用 Service 层处理业务逻辑
        service = GraphService(graph)
        node = await service.create_user_node(
            current_user.id,
            current_user.username,
            current_user.email
        )
        return ResponseUtil.success(data=node, message="用户同步成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/profile", response_model=SuccessResponse, summary="获取用户完整画像")
async def get_user_profile(
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        service = GraphService(graph)
        profile = await service.get_user_profile_complete(current_user.id)
        if not profile:
            return ResponseUtil.error(message="用户画像不存在")
        return ResponseUtil.success(data=profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digital-human", response_model=SuccessResponse, summary="创建数字人")
async def create_digital_human(
    digital_human_id: int,
    name: str,
    description: str,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        service = GraphService(graph)
        dh_node = await service.create_digital_human_with_owner(
            digital_human_id,
            name,
            description,
            current_user.id
        )
        if not dh_node:
            return ResponseUtil.error(message="创建数字人失败")
        return ResponseUtil.success(data=dh_node, message="数字人创建成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/digital-human/{digital_human_id}/analytics", response_model=SuccessResponse, summary="获取数字人分析")
async def get_digital_human_analytics(
    digital_human_id: int,
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        service = GraphService(graph)
        analytics = await service.get_digital_human_analytics(digital_human_id)
        return ResponseUtil.success(data=analytics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/statistics", response_model=SuccessResponse, summary="获取系统统计")
async def get_system_statistics(
    graph: GraphRepository = Depends(get_graph_repository),
    current_user: User = Depends(get_current_user)
):
    try:
        service = GraphService(graph)
        stats = await service.get_system_statistics()
        return ResponseUtil.success(data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))