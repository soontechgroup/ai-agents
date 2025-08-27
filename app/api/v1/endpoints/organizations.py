"""
组织管理API端点
所有操作使用POST请求，通过路径区分操作
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService
from app.models.graph.nodes import OrganizationNode

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ==================== 请求模型 ====================

class GetOrganizationRequest(BaseModel):
    """获取组织请求"""
    uid: str = Field(..., description="组织UID")


class GetEmployeesRequest(BaseModel):
    """获取组织员工请求"""
    uid: str = Field(..., description="组织UID")


class UpdateOrganizationRequest(BaseModel):
    """更新组织请求"""
    uid: str = Field(..., description="组织UID")
    data: OrganizationNode = Field(..., description="更新的数据")


class DeleteOrganizationRequest(BaseModel):
    """删除组织请求"""
    uid: str = Field(..., description="组织UID")


class SearchOrganizationsRequest(BaseModel):
    """搜索组织请求"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    industry: Optional[str] = Field(None, description="行业")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")


# ==================== API端点 ====================

@router.post("/create", response_model=SuccessResponse, summary="创建组织")
async def create_organization(
    organization: OrganizationNode,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """创建新组织"""
    try:
        created = await service.create_organization(organization)
        if created:
            return ResponseUtil.success(data=created, message="组织创建成功")
        return ResponseUtil.error(message="创建失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get", response_model=SuccessResponse, summary="获取组织详情")
async def get_organization(
    request: GetOrganizationRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取组织详细信息"""
    org = await service.get_organization(request.uid)
    if org:
        return ResponseUtil.success(data=org)
    return ResponseUtil.error(message="组织不存在")


@router.post("/update", response_model=SuccessResponse, summary="更新组织")
async def update_organization(
    request: UpdateOrganizationRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """更新组织信息"""
    # TODO: 在GraphService中实现update_organization方法
    return ResponseUtil.error(message="功能待实现")


@router.post("/delete", response_model=SuccessResponse, summary="删除组织")
async def delete_organization(
    request: DeleteOrganizationRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """删除组织"""
    # TODO: 在GraphService中实现delete_organization方法
    return ResponseUtil.error(message="功能待实现")


@router.post("/list", response_model=SuccessResponse, summary="获取组织列表")
async def list_organizations(
    request: SearchOrganizationsRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取组织列表"""
    from app.repositories.neomodel import OrganizationRepository
    repo = OrganizationRepository()
    
    result = repo.paginate(page=request.page, per_page=request.page_size)
    orgs = result["items"]
    
    # 转换为Pydantic模型
    org_models = [OrganizationNode.from_neomodel(org) for org in orgs]
    
    return ResponseUtil.success(data={
        "items": org_models,
        "total": result.get("total", len(org_models)),
        "page": request.page,
        "page_size": request.page_size
    })


@router.post("/search", response_model=SuccessResponse, summary="搜索组织")
async def search_organizations(
    request: SearchOrganizationsRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """搜索组织"""
    # TODO: 在GraphService中实现search_organizations方法
    from app.repositories.neomodel import OrganizationRepository
    repo = OrganizationRepository()
    
    if request.industry:
        orgs = repo.find_by_industry(request.industry)
    elif request.keyword:
        orgs = repo.search(request.keyword, ["name", "description"])
    else:
        result = repo.paginate(page=request.page, per_page=request.page_size)
        orgs = result["items"]
    
    # 转换为Pydantic模型
    org_models = [OrganizationNode.from_neomodel(org) for org in orgs]
    
    return ResponseUtil.success(data={
        "organizations": org_models,
        "count": len(org_models),
        "page": request.page,
        "page_size": request.page_size
    })


@router.post("/employees", response_model=SuccessResponse, summary="获取组织员工")
async def get_organization_employees(
    request: GetEmployeesRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取组织及其所有员工"""
    result = await service.get_organization_with_employees(request.uid)
    if result:
        return ResponseUtil.success(data=result)
    return ResponseUtil.error(message="组织不存在")