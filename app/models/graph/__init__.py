"""
图数据模型模块
提供Neo4j图数据库的节点和关系模型定义
"""

# 基础类
from .base import GraphEntity, Node, Relationship

# 类型定义
from .types import (
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

# 节点模型
from .nodes import (
    PersonNode,
    OrganizationNode
)

# 关系模型
from .relationships import (
    BaseRelationship,
    # 社交关系
    FriendRelationship,
    FamilyRelationship,
    KnowsRelationship,
    # 职业关系
    WorksAtRelationship,
    ColleagueRelationship,
    MentorshipRelationship,
    BusinessPartnershipRelationship
)

# 工厂类和方法
from .factory import (
    GraphModelFactory,
    create_node,
    create_relationship,
    register_node,
    register_relationship
)

__version__ = "1.0.0"

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
    
    # 节点模型
    "PersonNode",
    "OrganizationNode",
    
    # 关系模型
    "BaseRelationship",
    "FriendRelationship",
    "FamilyRelationship",
    "KnowsRelationship",
    "WorksAtRelationship",
    "ColleagueRelationship",
    "MentorshipRelationship",
    "BusinessPartnershipRelationship",
    
    # 工厂类和方法
    "GraphModelFactory",
    "create_node",
    "create_relationship",
    "register_node",
    "register_relationship",
]