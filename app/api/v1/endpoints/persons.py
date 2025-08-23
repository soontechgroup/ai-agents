"""
人员管理API端点
所有操作使用POST请求，通过路径区分操作
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService
from app.models.graph.nodes import PersonNode

router = APIRouter(prefix="/persons", tags=["Persons"])


# ==================== 请求模型 ====================

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


class BatchImportRequest(BaseModel):
    """批量导入请求"""
    persons: List[PersonNode] = Field(..., description="人员列表")


# ==================== API端点 ====================

@router.post("/create", response_model=SuccessResponse, summary="创建人员")
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


@router.post("/get", response_model=SuccessResponse, summary="获取人员详情")
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


@router.post("/update", response_model=SuccessResponse, summary="更新人员")
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


@router.post("/delete", response_model=SuccessResponse, summary="删除人员")
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


@router.post("/search", response_model=SuccessResponse, summary="搜索人员")
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


@router.post("/list", response_model=SuccessResponse, summary="获取人员列表")
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


@router.post("/network", response_model=SuccessResponse, summary="获取社交网络")
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


@router.post("/batch-import", response_model=SuccessResponse, summary="批量导入人员")
async def batch_import_persons(
    request: BatchImportRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """批量导入人员"""
    created = await service.import_persons_batch(request.persons)
    return ResponseUtil.success(
        data={"persons": created, "count": len(created)},
        message=f"成功导入{len(created)}个人员"
    )