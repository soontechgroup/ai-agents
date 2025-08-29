"""
分析相关请求模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class StatisticsRequest(BaseModel):
    """统计请求（可扩展）"""
    include_nodes: bool = Field(True, description="是否包含节点统计")
    include_relationships: bool = Field(True, description="是否包含关系统计")
    filter_label: Optional[str] = Field(None, description="过滤特定标签")