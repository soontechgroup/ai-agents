"""
图数据模型模块
提供Neo4j图数据库的动态节点和关系模型定义
"""

# 基础类
from app.models.graph.base import GraphEntity, Node, Relationship

# 类型定义
from app.models.graph.types import (
    # 通用枚举
    Gender,
    RelationshipStatus,
    Frequency,
    ConfidenceLevel,
    # 节点相关枚举
    OrganizationType,
    LocationType,
    EventType,
    ConceptCategory,
    # 关系相关枚举
    FriendshipLevel,
    FamilyRelationType,
    HierarchyType,
    CollaborationLevel,
    TransactionType,
    InvestmentType,
    DistanceUnit,
    TimeUnit,
    # 类型别名
    Coordinates,
    Priority,
    Rating,
    # 辅助函数
    confidence_to_level,
    level_to_confidence
)

# 动态模型
from app.models.graph.dynamic_entity import DynamicEntity
from app.models.graph.dynamic_relationship import DynamicRelationship

# 动态工厂
from app.models.graph.dynamic_factory import (
    DynamicGraphFactory,
    create_entity,
    create_relationship,
    infer_from_context
)

__version__ = "2.0.0"

__all__ = [
    # 基础类
    "GraphEntity",
    "Node",
    "Relationship",
    
    # 类型定义
    "Gender",
    "RelationshipStatus",
    "Frequency",
    "ConfidenceLevel",
    "OrganizationType",
    "LocationType",
    "EventType",
    "ConceptCategory",
    "FriendshipLevel",
    "FamilyRelationType",
    "HierarchyType",
    "CollaborationLevel",
    "TransactionType",
    "InvestmentType",
    "DistanceUnit",
    "TimeUnit",
    "Coordinates",
    "Priority",
    "Rating",
    "confidence_to_level",
    "level_to_confidence",
    
    # 动态模型
    "DynamicEntity",
    "DynamicRelationship",
    
    # 动态工厂
    "DynamicGraphFactory",
    "create_entity",
    "create_relationship",
    "infer_from_context",
]