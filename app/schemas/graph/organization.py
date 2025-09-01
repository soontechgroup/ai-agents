"""
组织相关请求模型
"""

from typing import Optional
from pydantic import BaseModel, Field
from app.models.graph.nodes import OrganizationNode


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