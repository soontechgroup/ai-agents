"""
社交关系模型
包含朋友、家庭等社交关系
"""

from typing import Optional, List
from datetime import date
from pydantic import Field, field_validator, model_validator

from .base import BaseRelationship
from ..types import (
    FriendshipLevel,
    FamilyRelationType,
    Frequency,
    RelationshipStatus
)


class FriendRelationship(BaseRelationship):
    """
    朋友关系模型
    表示两个人之间的友谊关系
    """
    
    # 友谊程度
    level: FriendshipLevel = Field(
        default=FriendshipLevel.FRIEND,
        description="友谊程度"
    )
    
    # 认识时间
    since: Optional[date] = Field(
        None,
        description="认识时间"
    )
    
    # 认识场景
    context: Optional[str] = Field(
        None,
        max_length=200,
        description="认识场景（如：大学同学、同事、网友等）"
    )
    
    # 联系频率
    contact_frequency: Frequency = Field(
        default=Frequency.MONTHLY,
        description="联系频率"
    )
    
    # 共同朋友数
    mutual_friends_count: int = Field(
        default=0,
        ge=0,
        description="共同朋友数量"
    )
    
    # 共同兴趣
    shared_interests: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="共同兴趣爱好"
    )
    
    # 最后联系时间
    last_contact: Optional[date] = Field(
        None,
        description="最后联系时间"
    )
    
    # 互动次数
    interaction_count: int = Field(
        default=0,
        ge=0,
        description="互动次数统计"
    )
    
    def __init__(self, **data):
        """初始化朋友关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "social"
        # 双向关系
        self.bidirectional = True
    
    @field_validator('since')
    @classmethod
    def validate_since_date(cls, v):
        """验证认识时间不能是未来"""
        if v and v > date.today():
            raise ValueError('Since date cannot be in the future')
        return v
    
    @field_validator('last_contact')
    @classmethod
    def validate_last_contact(cls, v):
        """验证最后联系时间不能是未来"""
        if v and v > date.today():
            raise ValueError('Last contact cannot be in the future')
        return v
    
    @model_validator(mode='after')
    def validate_contact_timeline(self):
        """验证联系时间线的一致性"""
        if self.last_contact and self.since and self.last_contact < self.since:
            raise ValueError('Last contact cannot be before first meeting')
        return self
    
    @model_validator(mode='after')
    def calculate_strength_from_level(self):
        """根据友谊程度自动设置关系强度"""
        if self.strength == 0.5:  # 默认值
            level_strength_map = {
                FriendshipLevel.ACQUAINTANCE: 0.3,
                FriendshipLevel.FRIEND: 0.5,
                FriendshipLevel.CLOSE_FRIEND: 0.75,
                FriendshipLevel.BEST_FRIEND: 0.9
            }
            self.strength = level_strength_map.get(self.level, 0.5)
        return self
    
    def calculate_friendship_score(self) -> float:
        """
        计算友谊分数（0-1）
        基于多个因素综合评估
        
        Returns:
            友谊分数
        """
        score = 0.0
        
        # 基础分数来自友谊等级
        level_scores = {
            FriendshipLevel.ACQUAINTANCE: 0.2,
            FriendshipLevel.FRIEND: 0.4,
            FriendshipLevel.CLOSE_FRIEND: 0.6,
            FriendshipLevel.BEST_FRIEND: 0.8
        }
        score += level_scores.get(self.level, 0.3)
        
        # 联系频率加分
        freq_scores = {
            Frequency.DAILY: 0.1,
            Frequency.WEEKLY: 0.08,
            Frequency.MONTHLY: 0.05,
            Frequency.QUARTERLY: 0.02,
            Frequency.YEARLY: 0.01,
            Frequency.RARELY: 0.0,
            Frequency.NEVER: -0.05
        }
        score += freq_scores.get(self.contact_frequency, 0.0)
        
        # 共同朋友加分（最多0.05）
        if self.mutual_friends_count > 0:
            score += min(0.05, self.mutual_friends_count * 0.01)
        
        # 共同兴趣加分（最多0.05）
        if self.shared_interests:
            score += min(0.05, len(self.shared_interests) * 0.01)
        
        return min(1.0, max(0.0, score))


class FamilyRelationship(BaseRelationship):
    """
    家庭关系模型
    表示家庭成员之间的关系
    """
    
    # 关系类型
    relation_type: FamilyRelationType = Field(
        ...,
        description="具体家庭关系类型"
    )
    
    # 是否血缘关系
    blood_relation: bool = Field(
        default=True,
        description="是否为血缘关系"
    )
    
    # 代际差距
    generation_gap: int = Field(
        default=0,
        ge=-5,
        le=5,
        description="代际差距（正数表示晚辈，负数表示长辈）"
    )
    
    # 同居状态
    living_together: bool = Field(
        default=False,
        description="是否同居"
    )
    
    # 法律关系
    legal_relation: bool = Field(
        default=True,
        description="是否有法律认可的关系"
    )
    
    # 关系建立时间（如结婚日期）
    established_date: Optional[date] = Field(
        None,
        description="关系建立时间"
    )
    
    # 家庭角色
    family_role: Optional[str] = Field(
        None,
        max_length=50,
        description="在家庭中的角色"
    )
    
    def __init__(self, **data):
        """初始化家庭关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "family"
        # 家庭关系通常是双向的（但描述可能不同）
        self.bidirectional = True
        # 家庭关系强度默认较高
        if self.strength == 0.5:  # 默认值
            self.strength = 0.8
    
    @model_validator(mode='after')
    def validate_generation_gap(self):
        """验证代际差距与关系类型的一致性"""
        rel_type = self.relation_type
        v = self.generation_gap
        # 验证代际关系
        if rel_type in [FamilyRelationType.PARENT]:
            if v >= 0:
                raise ValueError('Parent should have negative generation gap')
        elif rel_type in [FamilyRelationType.CHILD]:
            if v <= 0:
                raise ValueError('Child should have positive generation gap')
        elif rel_type in [FamilyRelationType.SIBLING, FamilyRelationType.SPOUSE]:
            if v != 0:
                raise ValueError('Sibling/Spouse should have zero generation gap')
        elif rel_type in [FamilyRelationType.GRANDPARENT]:
            if v >= -1:
                raise ValueError('Grandparent should have generation gap <= -2')
        elif rel_type in [FamilyRelationType.GRANDCHILD]:
            if v <= 1:
                raise ValueError('Grandchild should have generation gap >= 2')
        return self
    
    @model_validator(mode='after')
    def validate_blood_relation(self):
        """验证血缘关系与关系类型的一致性"""
        # 配偶和姻亲关系不是血缘关系
        if self.relation_type in [FamilyRelationType.SPOUSE, FamilyRelationType.IN_LAW]:
            if self.blood_relation:
                self.blood_relation = False  # 自动修正
        return self
    
    def get_reciprocal_type(self) -> Optional[FamilyRelationType]:
        """
        获取对等的关系类型
        例如：PARENT -> CHILD, CHILD -> PARENT
        
        Returns:
            对等的关系类型
        """
        reciprocal_map = {
            FamilyRelationType.PARENT: FamilyRelationType.CHILD,
            FamilyRelationType.CHILD: FamilyRelationType.PARENT,
            FamilyRelationType.SIBLING: FamilyRelationType.SIBLING,
            FamilyRelationType.SPOUSE: FamilyRelationType.SPOUSE,
            FamilyRelationType.GRANDPARENT: FamilyRelationType.GRANDCHILD,
            FamilyRelationType.GRANDCHILD: FamilyRelationType.GRANDPARENT,
            FamilyRelationType.UNCLE: None,  # 侄子/侄女需要更多信息
            FamilyRelationType.AUNT: None,   # 侄子/侄女需要更多信息
            FamilyRelationType.COUSIN: FamilyRelationType.COUSIN,
            FamilyRelationType.IN_LAW: FamilyRelationType.IN_LAW
        }
        return reciprocal_map.get(self.relation_type)
    
    def is_immediate_family(self) -> bool:
        """
        判断是否为直系亲属
        
        Returns:
            是否为直系亲属
        """
        immediate_types = {
            FamilyRelationType.PARENT,
            FamilyRelationType.CHILD,
            FamilyRelationType.SIBLING,
            FamilyRelationType.SPOUSE
        }
        return self.relation_type in immediate_types


class KnowsRelationship(BaseRelationship):
    """
    一般认识关系
    表示两个人之间的简单认识关系
    """
    
    # 如何认识
    how_met: Optional[str] = Field(
        None,
        max_length=200,
        description="如何认识的"
    )
    
    # 认识地点
    where_met: Optional[str] = Field(
        None,
        max_length=200,
        description="在哪里认识的"
    )
    
    # 认识时间
    when_met: Optional[date] = Field(
        None,
        description="何时认识的"
    )
    
    # 介绍人
    introduced_by: Optional[str] = Field(
        None,
        max_length=100,
        description="介绍人"
    )
    
    # 认识程度（0-1）
    familiarity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="熟悉程度"
    )
    
    # 是否互相认识
    mutual: bool = Field(
        default=True,
        description="是否互相认识"
    )
    
    def __init__(self, **data):
        """初始化认识关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "general"
        # 根据mutual设置双向性
        self.bidirectional = self.mutual
        # 一般认识关系强度较低
        if self.strength == 0.5:  # 默认值
            self.strength = self.familiarity * 0.5
    
    @field_validator('when_met')
    @classmethod
    def validate_when_met(cls, v):
        """验证认识时间不能是未来"""
        if v and v > date.today():
            raise ValueError('Meeting date cannot be in the future')
        return v