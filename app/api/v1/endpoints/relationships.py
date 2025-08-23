"""
关系管理API端点
所有操作使用POST请求，通过路径区分操作
"""

from fastapi import APIRouter, HTTPException, Depends

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.schemas.graph.relationship import EmploymentRequest, FriendshipRequest, PathRequest
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/relationships", tags=["Relationships"])


# ==================== API端点 ====================

@router.post("/add-employment", response_model=SuccessResponse, summary="添加雇佣关系")
async def add_employment(
    request: EmploymentRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """添加人员与组织的雇佣关系"""
    success = await service.add_employment(
        request.person_uid,
        request.organization_uid,
        request.position,
        request.department
    )
    if success:
        return ResponseUtil.success(message="雇佣关系添加成功")
    return ResponseUtil.error(message="添加失败，请检查人员和组织是否存在")


@router.post("/add-friendship", response_model=SuccessResponse, summary="添加朋友关系")
async def add_friendship(
    request: FriendshipRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """添加两个人之间的朋友关系"""
    success = await service.add_friendship(
        request.person1_uid,
        request.person2_uid
    )
    if success:
        return ResponseUtil.success(message="朋友关系添加成功")
    return ResponseUtil.error(message="添加失败，请检查人员是否存在")


@router.post("/find-shortest-path", response_model=SuccessResponse, summary="查找最短路径")
async def find_shortest_path(
    request: PathRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """查找两个人之间的最短路径"""
    path = await service.find_shortest_path(
        request.from_uid,
        request.to_uid
    )
    if path:
        return ResponseUtil.success(data=path)
    return ResponseUtil.error(message="未找到连接路径")