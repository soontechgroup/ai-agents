"""
关系相关请求模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class EmploymentRequest(BaseModel):
    """雇佣关系请求"""
    person_uid: str = Field(..., description="人员UID")
    organization_uid: str = Field(..., description="组织UID")
    position: str = Field(..., description="职位")
    department: str = Field(None, description="部门")


class FriendshipRequest(BaseModel):
    """朋友关系请求"""
    person1_uid: str = Field(..., description="人员1的UID")
    person2_uid: str = Field(..., description="人员2的UID")


class PathRequest(BaseModel):
    """路径查询请求"""
    from_uid: str = Field(..., description="起始节点UID")
    to_uid: str = Field(..., description="目标节点UID")


class ListRelationshipsRequest(BaseModel):
    """列出关系请求"""
    relationship_type: Optional[str] = Field(None, description="关系类型过滤")
    limit: int = Field(100, ge=1, le=500, description="返回数量限制")