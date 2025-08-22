"""
职业关系模型
包含工作、同事、商业等职业相关关系
"""

from typing import Optional, List
from datetime import date, datetime
from pydantic import Field, field_validator, model_validator

from .base import BaseRelationship
from ..types import (
    HierarchyType,
    CollaborationLevel,
    RelationshipStatus
)


class WorksAtRelationship(BaseRelationship):
    """
    工作关系模型
    表示人与组织之间的雇佣关系
    """
    
    # 职位信息
    position: str = Field(
        ...,
        max_length=100,
        description="职位名称"
    )
    
    department: Optional[str] = Field(
        None,
        max_length=100,
        description="所在部门"
    )
    
    # 工作时间
    start_date: date = Field(
        ...,
        description="入职日期"
    )
    
    end_date: Optional[date] = Field(
        None,
        description="离职日期"
    )
    
    # 工作状态
    is_current: bool = Field(
        default=True,
        description="是否当前在职"
    )
    
    employment_type: Optional[str] = Field(
        None,
        max_length=50,
        description="雇佣类型（全职、兼职、合同工、实习等）"
    )
    
    # 薪资信息（可选，敏感信息）
    salary_range: Optional[str] = Field(
        None,
        max_length=50,
        description="薪资范围"
    )
    
    # 工作地点
    location: Optional[str] = Field(
        None,
        max_length=100,
        description="工作地点"
    )
    
    # 汇报关系
    reports_to: Optional[str] = Field(
        None,
        max_length=100,
        description="直接上级ID"
    )
    
    # 管理团队规模
    team_size: Optional[int] = Field(
        None,
        ge=0,
        description="管理团队规模"
    )
    
    # 主要职责
    responsibilities: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="主要职责"
    )
    
    # 成就
    achievements: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="主要成就"
    )
    
    def __init__(self, **data):
        """初始化工作关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "professional"
        # 工作关系是单向的（人->组织）
        self.bidirectional = False
    
    @model_validator(mode='after')
    def validate_employment_consistency(self):
        """验证工作日期和状态的一致性"""
        if self.end_date:
            if self.end_date < self.start_date:
                raise ValueError('End date cannot be before start date')
            # 如果有结束日期，不应该是当前在职
            if self.is_current:
                self.is_current = False  # 自动修正
        return self
    
    @field_validator('team_size')
    @classmethod
    def validate_team_size(cls, v):
        """验证团队规模的合理性"""
        # 基本验证，具体的职位相关验证可以在model_validator中进行
        return v
    
    def calculate_tenure(self) -> float:
        """
        计算任职时长
        
        Returns:
            任职年数
        """
        end = self.end_date or date.today()
        delta = end - self.start_date
        return delta.days / 365.25
    
    def is_management_position(self) -> bool:
        """
        判断是否为管理职位
        
        Returns:
            是否为管理职位
        """
        if self.team_size and self.team_size > 0:
            return True
        
        position_lower = self.position.lower()
        management_keywords = ['manager', 'director', 'lead', 'head', 'supervisor', 'chief', 'vp', 'president']
        return any(keyword in position_lower for keyword in management_keywords)


class ColleagueRelationship(BaseRelationship):
    """
    同事关系模型
    表示两个人之间的工作伙伴关系
    """
    
    # 所在组织
    organization: str = Field(
        ...,
        max_length=100,
        description="共同所在的组织"
    )
    
    # 部门
    department: Optional[str] = Field(
        None,
        max_length=100,
        description="共同部门"
    )
    
    # 层级关系
    hierarchy: HierarchyType = Field(
        default=HierarchyType.PEER,
        description="层级关系"
    )
    
    # 协作程度
    collaboration_level: CollaborationLevel = Field(
        default=CollaborationLevel.MEDIUM,
        description="协作密切程度"
    )
    
    # 共事时间
    start_date: date = Field(
        ...,
        description="开始共事时间"
    )
    
    end_date: Optional[date] = Field(
        None,
        description="结束共事时间"
    )
    
    # 是否当前同事
    is_current: bool = Field(
        default=True,
        description="是否当前同事"
    )
    
    # 共同项目
    shared_projects: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="共同参与的项目"
    )
    
    # 工作互动频率
    interaction_frequency: Optional[str] = Field(
        None,
        max_length=50,
        description="工作互动频率"
    )
    
    # 专业评价
    professional_rating: Optional[float] = Field(
        None,
        ge=0.0,
        le=5.0,
        description="专业能力评分"
    )
    
    def __init__(self, **data):
        """初始化同事关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "professional"
        # 同事关系可以是双向的（平级）或单向的（上下级）
        self.bidirectional = (self.hierarchy == HierarchyType.PEER)
    
    @field_validator('hierarchy')
    @classmethod
    def validate_hierarchy(cls, v):
        """验证层级关系"""
        return v
    
    @model_validator(mode='after')
    def validate_colleague_dates(self):
        """验证共事日期的合理性"""
        if self.end_date:
            if self.end_date < self.start_date:
                raise ValueError('End date cannot be before start date')
            if self.is_current:
                self.is_current = False  # 自动修正
        return self
    
    @model_validator(mode='after')
    def calculate_strength_from_collaboration(self):
        """根据协作程度自动设置关系强度"""
        if self.strength == 0.5:  # 默认值
            level_strength_map = {
                CollaborationLevel.NONE: 0.1,
                CollaborationLevel.LOW: 0.3,
                CollaborationLevel.MEDIUM: 0.5,
                CollaborationLevel.HIGH: 0.7,
                CollaborationLevel.INTENSIVE: 0.9
            }
            self.strength = level_strength_map.get(self.collaboration_level, 0.5)
        return self
    
    def get_reciprocal_hierarchy(self) -> Optional[HierarchyType]:
        """
        获取对等的层级关系
        
        Returns:
            对等的层级关系
        """
        reciprocal_map = {
            HierarchyType.SUPERIOR: HierarchyType.SUBORDINATE,
            HierarchyType.SUBORDINATE: HierarchyType.SUPERIOR,
            HierarchyType.PEER: HierarchyType.PEER,
            HierarchyType.MENTOR: HierarchyType.MENTEE,
            HierarchyType.MENTEE: HierarchyType.MENTOR
        }
        return reciprocal_map.get(self.hierarchy)


class MentorshipRelationship(BaseRelationship):
    """
    师徒关系模型
    表示指导与被指导的关系
    """
    
    # 指导方向（从导师视角）
    is_mentor: bool = Field(
        ...,
        description="是否为导师（True：导师，False：学徒）"
    )
    
    # 指导领域
    domain: str = Field(
        ...,
        max_length=100,
        description="指导领域"
    )
    
    # 专业技能
    skills_taught: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="传授的技能"
    )
    
    # 指导形式
    mentorship_type: Optional[str] = Field(
        None,
        max_length=50,
        description="指导形式（正式、非正式、项目制等）"
    )
    
    # 指导频率
    meeting_frequency: Optional[str] = Field(
        None,
        max_length=50,
        description="会面频率"
    )
    
    # 指导时长
    duration_months: Optional[int] = Field(
        None,
        ge=0,
        description="指导时长（月）"
    )
    
    # 是否正在进行
    is_ongoing: bool = Field(
        default=True,
        description="是否正在进行"
    )
    
    # 成果
    outcomes: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="指导成果"
    )
    
    # 满意度
    satisfaction_rating: Optional[float] = Field(
        None,
        ge=0.0,
        le=5.0,
        description="满意度评分"
    )
    
    def __init__(self, **data):
        """初始化师徒关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "professional"
        # 师徒关系是单向的
        self.bidirectional = False
        # 师徒关系通常强度较高
        if self.strength == 0.5:  # 默认值
            self.strength = 0.7
    
    def get_role(self) -> str:
        """
        获取角色
        
        Returns:
            'mentor' 或 'mentee'
        """
        return "mentor" if self.is_mentor else "mentee"


class BusinessPartnershipRelationship(BaseRelationship):
    """
    商业伙伴关系模型
    表示商业合作关系
    """
    
    # 合作类型
    partnership_type: str = Field(
        ...,
        max_length=50,
        description="合作类型（供应商、客户、合作伙伴等）"
    )
    
    # 合同状态
    contract_status: Optional[str] = Field(
        None,
        max_length=50,
        description="合同状态"
    )
    
    # 合作开始时间
    start_date: date = Field(
        ...,
        description="合作开始时间"
    )
    
    # 合作结束时间
    end_date: Optional[date] = Field(
        None,
        description="合作结束时间"
    )
    
    # 合作价值
    deal_value: Optional[float] = Field(
        None,
        ge=0,
        description="合作价值/交易额"
    )
    
    # 战略重要性
    strategic_importance: Optional[str] = Field(
        None,
        max_length=20,
        description="战略重要性（低、中、高、关键）"
    )
    
    # 合作项目
    projects: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="合作项目列表"
    )
    
    # 主要联系人
    key_contacts: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="主要联系人"
    )
    
    # 满意度
    satisfaction_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="合作满意度"
    )
    
    def __init__(self, **data):
        """初始化商业伙伴关系"""
        super().__init__(**data)
        # 设置默认分类
        if not self.category:
            self.category = "business"
        # 商业关系通常是双向的
        self.bidirectional = True
    
    @model_validator(mode='after')
    def validate_partnership_dates(self):
        """验证合作日期的合理性"""
        if self.end_date and self.end_date < self.start_date:
            raise ValueError('End date cannot be before start date')
        return self
    
    def is_active_partnership(self) -> bool:
        """
        判断是否为活跃合作
        
        Returns:
            是否活跃
        """
        if self.end_date and self.end_date < date.today():
            return False
        return self.status == RelationshipStatus.ACTIVE