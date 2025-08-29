"""
人员相关请求模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.graph.nodes import PersonNode


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

