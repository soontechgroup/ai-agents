"""
关系模型包
"""

from .base import BaseRelationship
from .social import FriendRelationship, FamilyRelationship, KnowsRelationship
from .professional import (
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