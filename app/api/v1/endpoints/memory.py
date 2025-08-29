"""
记忆体系统API端点
统一管理人员、组织和关系的所有操作
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.schemas.graph.relationship import EmploymentRequest, FriendshipRequest, PathRequest
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService
from app.models.graph.nodes import PersonNode, OrganizationNode

# 创建主路由
router = APIRouter(prefix="/memory", tags=["Memory System"])

# 创建子路由
persons_router = APIRouter(prefix="/persons", tags=["Memory - Persons"])
organizations_router = APIRouter(prefix="/organizations", tags=["Memory - Organizations"])
relationships_router = APIRouter(prefix="/relationships", tags=["Memory - Relationships"])


# ==================== 请求模型 ====================

# ========== Person请求模型 ==========
class GetPersonRequest(BaseModel):
    """获取人员请求"""
    uid: str = Field(..., description="人员UID")


class UpdatePersonRequest(BaseModel):
    """更新人员请求"""
    uid: str = Field(..., description="人员UID")
    data: PersonNode = Field(..., description="更新的数据")


class DeletePersonRequest(BaseModel):
    """删除人员请求"""
    uid: str = Field(..., description="人员UID")


class SearchPersonsRequest(BaseModel):
    """搜索人员请求"""
    keyword: str = Field(..., description="搜索关键词")
    page: Optional[int] = Field(1, ge=1, description="页码")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="每页数量")


class ListPersonsRequest(BaseModel):
    """列表查询请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    filters: Optional[dict] = Field(None, description="过滤条件")


class PersonNetworkRequest(BaseModel):
    """社交网络请求"""
    uid: str = Field(..., description="人员UID")
    depth: int = Field(2, ge=1, le=5, description="网络深度")


# ========== Organization请求模型 ==========
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


# ========== Relationship请求模型 ==========
class ListRelationshipsRequest(BaseModel):
    """列出关系请求"""
    relationship_type: Optional[str] = Field(None, description="关系类型过滤")
    limit: int = Field(100, ge=1, le=500, description="返回数量限制")


# ==================== Person端点 ====================

@persons_router.post("/create", response_model=SuccessResponse, summary="创建人员")
async def create_person(
    person: PersonNode,
    service: GraphService = Depends(get_graph_service)
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """创建新人员"""
    try:
        created = await service.create_person(person)
        if created:
            return ResponseUtil.success(data=created, message="人员创建成功")
        return ResponseUtil.error(message="创建失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@persons_router.post("/get", response_model=SuccessResponse, summary="获取人员详情")
async def get_person(
    request: GetPersonRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取人员详细信息"""
    person = await service.get_person(request.uid)
    if person:
        return ResponseUtil.success(data=person)
    return ResponseUtil.error(message="人员不存在")


@persons_router.post("/update", response_model=SuccessResponse, summary="更新人员")
async def update_person(
    request: UpdatePersonRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """更新人员信息"""
    updated = await service.update_person(request.uid, request.data)
    if updated:
        return ResponseUtil.success(data=updated, message="更新成功")
    return ResponseUtil.error(message="人员不存在或更新失败")


@persons_router.post("/delete", response_model=SuccessResponse, summary="删除人员")
async def delete_person(
    request: DeletePersonRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """删除人员"""
    success = await service.delete_person(request.uid)
    if success:
        return ResponseUtil.success(message="删除成功")
    return ResponseUtil.error(message="删除失败")


@persons_router.post("/search", response_model=SuccessResponse, summary="搜索人员")
async def search_persons(
    request: SearchPersonsRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """搜索人员"""
    persons = await service.search_persons(request.keyword)
    return ResponseUtil.success(
        data={
            "persons": persons,
            "count": len(persons),
            "page": request.page,
            "page_size": request.page_size
        },
        message=f"找到{len(persons)}个匹配的人员"
    )


@persons_router.post("/list", response_model=SuccessResponse, summary="获取人员列表")
async def list_persons(
    request: ListPersonsRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取人员列表（带分页）"""
    from app.repositories.neomodel import PersonRepository
    repo = PersonRepository()
    
    # 获取分页数据
    result = repo.paginate(
        page=request.page,
        per_page=request.page_size,
        **(request.filters or {})
    )
    
    # 转换为Pydantic模型
    items = [PersonNode.from_neomodel(item) for item in result["items"]]
    
    return ResponseUtil.success(data={
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["per_page"],
        "pages": result["pages"]
    })


@persons_router.post("/network", response_model=SuccessResponse, summary="获取社交网络")
async def get_person_network(
    request: PersonNetworkRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取人员的社交网络"""
    network = await service.get_person_network(request.uid, request.depth)
    if network:
        return ResponseUtil.success(data=network)
    return ResponseUtil.error(message="人员不存在")


# ==================== Organization端点 ====================

@organizations_router.post("/create", response_model=SuccessResponse, summary="创建组织")
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


@organizations_router.post("/get", response_model=SuccessResponse, summary="获取组织详情")
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


@organizations_router.post("/update", response_model=SuccessResponse, summary="更新组织")
async def update_organization(
    request: UpdateOrganizationRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """更新组织信息"""
    # TODO: 在GraphService中实现update_organization方法
    return ResponseUtil.error(message="功能待实现")


@organizations_router.post("/delete", response_model=SuccessResponse, summary="删除组织")
async def delete_organization(
    request: DeleteOrganizationRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """删除组织"""
    # TODO: 在GraphService中实现delete_organization方法
    return ResponseUtil.error(message="功能待实现")


@organizations_router.post("/list", response_model=SuccessResponse, summary="获取组织列表")
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


@organizations_router.post("/search", response_model=SuccessResponse, summary="搜索组织")
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


@organizations_router.post("/employees", response_model=SuccessResponse, summary="获取组织员工")
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


# ==================== Relationship端点 ====================

@relationships_router.post("/add-employment", response_model=SuccessResponse, summary="添加雇佣关系")
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


@relationships_router.post("/add-friendship", response_model=SuccessResponse, summary="添加朋友关系")
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


@relationships_router.post("/list", response_model=SuccessResponse, summary="获取所有关系")
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


@relationships_router.post("/find-shortest-path", response_model=SuccessResponse, summary="查找最短路径")
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


# ==================== 注册子路由到主路由 ====================
router.include_router(persons_router)
router.include_router(organizations_router)
router.include_router(relationships_router)