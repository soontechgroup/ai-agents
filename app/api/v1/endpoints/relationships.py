"""
关系管理API端点
所有操作使用POST请求，通过路径区分操作
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.schemas.graph.relationship import EmploymentRequest, FriendshipRequest, PathRequest
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/relationships", tags=["Relationships"])


# ==================== 请求模型 ====================

class ListRelationshipsRequest(BaseModel):
    """列出关系请求"""
    relationship_type: Optional[str] = Field(None, description="关系类型过滤")
    limit: int = Field(100, ge=1, le=500, description="返回数量限制")


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
    try:
        # 直接调用服务层处理，服务层会处理名字和UID的转换
        success = await service.add_friendship(
            request.person1_uid,  # 可以是UID或名字
            request.person2_uid   # 可以是UID或名字
        )
        
        if success:
            return ResponseUtil.success(message="朋友关系添加成功")
        
        return ResponseUtil.error(message="添加失败，请检查人物是否存在")
        
    except Exception as e:
        from app.core.logger import logger
        logger.exception(f"添加朋友关系异常: {str(e)}")
        return ResponseUtil.error(message=f"添加关系失败: {str(e)}")


@router.post("/list", response_model=SuccessResponse, summary="获取所有关系")
async def list_relationships(
    request: ListRelationshipsRequest = ListRelationshipsRequest(),
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取图数据库中的所有关系"""
    try:
        # 使用服务层方法获取关系列表
        result = await service.list_relationships(
            relationship_type=request.relationship_type,
            limit=request.limit
        )
        
        return ResponseUtil.success(data=result)
        
    except Exception as e:
        from app.core.logger import logger
        logger.exception(f"获取关系列表失败: {str(e)}")
        return ResponseUtil.error(message=f"获取关系失败: {str(e)}")


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