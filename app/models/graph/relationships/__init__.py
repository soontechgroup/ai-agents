"""
关系模型包
"""

from app.models.graph.relationships.base import BaseRelationship
from app.models.graph.relationships.social import FriendRelationship, FamilyRelationship, KnowsRelationship
from app.models.graph.relationships.professional import (
    WorksAtRelationship,
    ColleagueRelationship,
    MentorshipRelationship,
    BusinessPartnershipRelationship
)

__all__ = [
    # 基类
    "BaseRelationship",
    
    # 社交关系
    "FriendRelationship",
    "FamilyRelationship",
    "KnowsRelationship",
    
    # 职业关系
    "WorksAtRelationship",
    "ColleagueRelationship",
    "MentorshipRelationship",
    "BusinessPartnershipRelationship",
]