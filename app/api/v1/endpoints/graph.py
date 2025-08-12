"""
Neo4j 图数据库 API 端点
用于测试和演示 Neo4j 功能
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from ....services.graph_service import graph_service
from ....guards.auth import get_current_user
from ....schemas.user import User
from ....schemas.CommonResponse import SuccessResponse
from ....utils.response import ResponseUtil

router = APIRouter(prefix="/graph", tags=["Graph Database"])


# ==================== 请求模型 ====================

class CreateNodeRequest(BaseModel):
    """创建节点请求"""
    label: str
    properties: Dict[str, Any]


class CreateRelationshipRequest(BaseModel):
    """创建关系请求"""
    from_node_id: int
    to_node_id: int
    rel_type: str
    properties: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    """搜索请求"""
    label: str
    keyword: str
    properties: List[str]


class FindNodesRequest(BaseModel):
    """查找节点请求"""
    label: str
    limit: int = 10


class GetMessagesRequest(BaseModel):
    """获取消息请求"""
    conversation_id: str


class GetPopularRequest(BaseModel):
    """获取热门数字人请求"""
    limit: int = 10


# ==================== 测试端点 ====================

@router.post("/test/create-node", response_model=SuccessResponse, summary="测试创建节点")
async def test_create_node(request: CreateNodeRequest):
    """
    测试创建节点
    
    Example:
        POST /graph/test/create-node
        {
            "label": "TestUser",
            "properties": {
                "name": "张三",
                "age": 25
            }
        }
    """
    try:
        from ....utils.neo4j_util import neo4j_util
        node = neo4j_util.create_node(request.label, request.properties)
        return ResponseUtil.success(data=node, message="节点创建成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/create-relationship", response_model=SuccessResponse, summary="测试创建关系")
async def test_create_relationship(request: CreateRelationshipRequest):
    """
    测试创建关系
    
    Example:
        POST /graph/test/create-relationship
        {
            "from_node_id": 1,
            "to_node_id": 2,
            "rel_type": "FOLLOWS"
        }
    """
    try:
        from ....utils.neo4j_util import neo4j_util
        success = neo4j_util.create_relationship(
            request.from_node_id,
            request.to_node_id,
            request.rel_type,
            request.properties
        )
        return ResponseUtil.success(
            data={"success": success},
            message="关系创建成功" if success else "关系创建失败"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/find-nodes", response_model=SuccessResponse, summary="测试查找节点")
async def test_find_nodes(request: FindNodesRequest):
    """
    测试查找节点
    
    Example:
        POST /graph/test/find-nodes
        {
            "label": "User",
            "limit": 5
        }
    """
    try:
        from ....utils.neo4j_util import neo4j_util
        nodes = neo4j_util.find_all_nodes(request.label, request.limit)
        return ResponseUtil.success(
            data={"nodes": nodes, "count": len(nodes)},
            message="查询成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/search", response_model=SuccessResponse, summary="测试搜索功能")
async def test_search(request: SearchRequest):
    """
    测试搜索功能
    
    Example:
        POST /graph/test/search
        {
            "label": "User",
            "keyword": "张",
            "properties": ["name", "username"]
        }
    """
    try:
        from ....utils.neo4j_util import neo4j_util
        nodes = neo4j_util.search_nodes_by_keyword(
            request.label,
            request.keyword,
            request.properties
        )
        return ResponseUtil.success(
            data={"nodes": nodes, "count": len(nodes)},
            message="搜索成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 业务端点 ====================

@router.post("/sync/user", response_model=SuccessResponse, summary="同步用户到图数据库")
async def sync_user_to_graph(current_user: User = Depends(get_current_user)):
    """
    同步当前用户到图数据库
    """
    try:
        node = await graph_service.create_user_node(
            current_user.id,
            current_user.username,
            current_user.email
        )
        return ResponseUtil.success(data=node, message="用户同步成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/digital-humans", response_model=SuccessResponse, summary="获取用户的数字人")
async def get_user_digital_humans(current_user: User = Depends(get_current_user)):
    """
    获取用户的数字人（从图数据库）
    """
    try:
        digital_humans = await graph_service.get_user_digital_humans(current_user.id)
        return ResponseUtil.success(
            data={"digital_humans": digital_humans, "count": len(digital_humans)},
            message="查询成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/popular/digital-humans", response_model=SuccessResponse, summary="获取热门数字人")
async def get_popular_digital_humans(request: GetPopularRequest):
    """
    获取热门数字人
    
    Example:
        POST /graph/popular/digital-humans
        {
            "limit": 10
        }
    """
    try:
        popular = await graph_service.get_popular_digital_humans(request.limit)
        return ResponseUtil.success(
            data={"digital_humans": popular, "count": len(popular)},
            message="查询成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similar-users", response_model=SuccessResponse, summary="查找相似用户")
async def find_similar_users(current_user: User = Depends(get_current_user)):
    """
    查找相似用户
    """
    try:
        similar = await graph_service.find_similar_users(current_user.id)
        return ResponseUtil.success(
            data={"users": similar, "count": len(similar)},
            message="查询成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/messages", response_model=SuccessResponse, summary="获取对话消息")
async def get_conversation_messages(request: GetMessagesRequest):
    """
    获取对话消息
    
    Example:
        POST /graph/conversation/messages
        {
            "conversation_id": "conv_123456"
        }
    """
    try:
        messages = await graph_service.get_conversation_messages(request.conversation_id)
        return ResponseUtil.success(
            data={"messages": messages, "count": len(messages)},
            message="查询成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))