from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.common_response import PaginatedResponse, PaginationMeta


class PersonalityConfig(BaseModel):
    """性格特征配置"""
    professionalism: int = Field(default=80, ge=0, le=100, description="专业性 (0-100)")
    friendliness: int = Field(default=90, ge=0, le=100, description="友善度 (0-100)")
    humor: int = Field(default=60, ge=0, le=100, description="幽默感 (0-100)")


class DigitalHumanCreate(BaseModel):
    """创建数字人模板请求模型"""
    name: str = Field(..., max_length=100, description="数字人名称")
    short_description: Optional[str] = Field(None, max_length=200, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    type: str = Field(default="专业助手", description="数字人类型")
    skills: Optional[List[str]] = Field(default=[], description="专业领域技能")
    personality: Optional[PersonalityConfig] = Field(default_factory=PersonalityConfig, description="性格特征")
    conversation_style: Optional[str] = Field(default="专业严谨", description="对话风格")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2, description="AI温度参数")
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192, description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(default=False, description="是否公开模板")


class DigitalHumanUpdate(BaseModel):
    """更新数字人模板请求模型"""
    name: Optional[str] = Field(None, max_length=100, description="数字人名称")
    short_description: Optional[str] = Field(None, max_length=200, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    type: Optional[str] = Field(None, description="数字人类型")
    skills: Optional[List[str]] = Field(None, description="专业领域技能")
    personality: Optional[PersonalityConfig] = Field(None, description="性格特征")
    conversation_style: Optional[str] = Field(None, description="对话风格")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="AI温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(None, description="是否公开模板")
    is_active: Optional[bool] = Field(None, description="是否启用模板（启用后可用于对话）")


class DigitalHumanResponse(BaseModel):
    """数字人模板响应模型"""
    id: int = Field(..., description="数字人ID")
    name: str = Field(..., description="数字人名称")
    short_description: Optional[str] = Field(None, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    type: str = Field(..., description="数字人类型")
    skills: Optional[List[str]] = Field(None, description="专业领域技能")
    personality: Optional[Dict[str, int]] = Field(None, description="性格特征")
    conversation_style: Optional[str] = Field(None, description="对话风格")
    temperature: float = Field(..., description="AI温度参数")
    max_tokens: int = Field(..., description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_active: bool = Field(..., description="模板是否启用（启用后可用于创建对话）")
    is_public: bool = Field(..., description="是否公开模板")
    owner_id: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_trained_at: Optional[datetime] = Field(None, description="最后训练时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class DigitalHumanDetailRequest(BaseModel):
    """获取数字人详情请求模型"""
    id: int = Field(..., description="数字人ID")


class DigitalHumanUpdateRequest(BaseModel):
    """更新数字人模板请求模型（包含ID）"""
    id: int = Field(..., description="数字人ID")
    name: Optional[str] = Field(None, max_length=100, description="数字人名称")
    short_description: Optional[str] = Field(None, max_length=200, description="简短描述")
    detailed_description: Optional[str] = Field(None, description="详细介绍")
    type: Optional[str] = Field(None, description="数字人类型")
    skills: Optional[List[str]] = Field(None, description="专业领域技能")
    personality: Optional[PersonalityConfig] = Field(None, description="性格特征")
    conversation_style: Optional[str] = Field(None, description="对话风格")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="AI温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="最大token数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(None, description="是否公开模板")
    is_active: Optional[bool] = Field(None, description="是否启用模板（启用后可用于对话）")


class DigitalHumanDeleteRequest(BaseModel):
    """删除数字人请求模型"""
    id: int = Field(..., description="数字人ID")


class DigitalHumanPageRequest(BaseModel):
    """数字人分页请求模型"""
    page: int = Field(default=1, ge=1, description="页码,从1开始")
    size: int = Field(default=10, ge=1, le=100, description="每页数量,最大100")
    search: Optional[str] = Field(None, description="搜索关键词(名称、描述)")
    include_public: bool = Field(default=True, description="是否包含公开模板")


class DigitalHumanPageResponse(PaginatedResponse[List[DigitalHumanResponse]]):
    """数字人分页响应模型"""
    pass


class DigitalHumanTrainRequest(BaseModel):
    """数字人训练请求模型"""
    digital_human_id: int = Field(..., description="数字人ID")
    message: str = Field(..., description="训练消息内容")


class MemoryGraphNode(BaseModel):
    """记忆图谱节点"""
    id: str = Field(..., description="节点ID")
    label: str = Field(..., description="节点标签")
    type: str = Field(..., description="节点类型")
    size: float = Field(..., description="节点大小")
    confidence: float = Field(..., description="置信度")
    properties: Dict[str, Any] = Field(default_factory=dict, description="节点属性")
    updated_at: Optional[str] = Field(None, description="更新时间")


class MemoryGraphEdge(BaseModel):
    """记忆图谱边"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    type: str = Field(..., description="关系类型")
    confidence: float = Field(default=0.5, description="置信度")
    properties: Dict[str, Any] = Field(default_factory=dict, description="边属性")


class MemoryGraphStatistics(BaseModel):
    """记忆图谱统计信息"""
    total_nodes: int = Field(..., description="总节点数")
    total_edges: int = Field(..., description="总边数")
    displayed_nodes: int = Field(..., description="显示的节点数")
    displayed_edges: int = Field(..., description="显示的边数")
    categories: Dict[str, int] = Field(..., description="各类型节点数量")


class MemoryGraphResponse(BaseModel):
    """记忆图谱响应"""
    nodes: List[MemoryGraphNode] = Field(..., description="节点列表")
    edges: List[MemoryGraphEdge] = Field(..., description="边列表")
    statistics: MemoryGraphStatistics = Field(..., description="统计信息")


class MemoryGraphRequest(BaseModel):
    """记忆图谱请求"""
    digital_human_id: int = Field(..., description="数字人ID")
    limit: int = Field(default=100, ge=1, le=500, description="返回的最大节点数")
    node_types: Optional[List[str]] = Field(None, description="要筛选的节点类型列表")


class TrainingMessagesRequest(BaseModel):
    """获取训练消息请求"""
    digital_human_id: int = Field(..., description="数字人ID")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页数量")


class TrainingMessageResponse(BaseModel):
    """训练消息响应"""
    id: int = Field(..., description="消息ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    extracted_knowledge: Optional[Dict[str, Any]] = Field(None, description="抽取的知识")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class TrainingMessagesPageResponse(PaginatedResponse[List[TrainingMessageResponse]]):
    """训练消息分页响应"""
    pass


class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    digital_human_id: int = Field(..., description="数字人ID")
    query: str = Field(..., description="搜索关键词")
    node_types: Optional[List[str]] = Field(None, description="要筛选的节点类型列表")
    limit: int = Field(default=50, ge=1, le=200, description="返回的最大结果数")


class MemoryDetailRequest(BaseModel):
    """记忆详情请求"""
    digital_human_id: int = Field(..., description="数字人ID")
    node_id: str = Field(..., description="节点ID")
    include_relations: bool = Field(default=True, description="是否包含相关关系")
    relation_depth: int = Field(default=1, ge=1, le=3, description="关系查询深度")


class MemoryDetailResponse(BaseModel):
    """记忆详情响应"""
    node: MemoryGraphNode = Field(..., description="节点详情")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="相关关系")
    connected_nodes: List[MemoryGraphNode] = Field(default_factory=list, description="相关联的节点")


class MemoryStatsRequest(BaseModel):
    """记忆统计请求"""
    digital_human_id: int = Field(..., description="数字人ID")
    include_timeline: bool = Field(default=False, description="是否包含时间线统计")


class MemoryStatsResponse(BaseModel):
    """记忆统计响应"""
    total_nodes: int = Field(..., description="总节点数")
    total_edges: int = Field(..., description="总关系数")
    node_categories: Dict[str, int] = Field(..., description="各类型节点数量")
    edge_types: Dict[str, int] = Field(..., description="各类型关系数量")
    network_density: float = Field(..., description="网络密度")
    avg_connections_per_node: float = Field(..., description="节点平均连接数")
    timeline: Optional[List[Dict[str, Any]]] = Field(None, description="时间线统计")
