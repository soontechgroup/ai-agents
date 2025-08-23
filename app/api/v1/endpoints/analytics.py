"""
图数据库分析API端点
所有操作使用POST请求，通过路径区分操作
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.core.models import User
from app.guards.auth import get_current_user
from app.schemas.common_response import SuccessResponse
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/analytics", tags=["Graph Analytics"])


# ==================== 请求模型 ====================

class StatisticsRequest(BaseModel):
    """统计请求（可扩展）"""
    include_nodes: bool = Field(True, description="是否包含节点统计")
    include_relationships: bool = Field(True, description="是否包含关系统计")
    filter_label: Optional[str] = Field(None, description="过滤特定标签")


# ==================== API端点 ====================

@router.post("/get-statistics", response_model=SuccessResponse, summary="获取系统统计")
async def get_system_statistics(
    request: StatisticsRequest = StatisticsRequest(),
    service: GraphService = Depends(get_graph_service),
    current_user: User = Depends(get_current_user)
):
    """获取图数据库系统统计信息"""
    stats = await service.get_system_statistics()
    
    # 根据请求参数过滤结果
    result = {}
    if request.include_nodes:
        result["nodes"] = stats.get("nodes", {})
        result["total_nodes"] = stats.get("total_nodes", 0)
    
    if request.include_relationships:
        result["relationships"] = stats.get("relationships", {})
        result["total_relationships"] = stats.get("total_relationships", 0)
    
    # 如果指定了标签过滤
    if request.filter_label and "nodes" in result:
        filtered_nodes = {k: v for k, v in result["nodes"].items() if k == request.filter_label}
        result["nodes"] = filtered_nodes
    
    return ResponseUtil.success(data=result)