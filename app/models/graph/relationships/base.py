"""
关系模型基类
提供所有关系类型的共同基础
"""

from typing import Optional
from datetime import datetime
from pydantic import Field, field_validator, model_validator

from ..base import Relationship
from ..types import RelationshipStatus, ConfidenceLevel, confidence_to_level


class BaseRelationship(Relationship):
    """
    增强的关系基类
    添加了通用的关系属性
    """
    
    # 关系状态
    status: RelationshipStatus = Field(
        default=RelationshipStatus.ACTIVE,
        description="关系状态"
    )
    
    # 关系分类
    category: Optional[str] = Field(
        None,
        max_length=50,
        description="关系分类"
    )
    
    # 关系子类型
    subtype: Optional[str] = Field(
        None,
        max_length=50,
        description="关系子类型"
    )
    
    # 验证状态
    verified: bool = Field(
        default=False,
        description="是否已验证"
    )
    
    # 验证时间
    verified_at: Optional[datetime] = Field(
        None,
        description="验证时间"
    )
    
    # 验证者
    verified_by: Optional[str] = Field(
        None,
        max_length=100,
        description="验证者ID或名称"
    )
    
    # 来源
    source: Optional[str] = Field(
        None,
        max_length=100,
        description="关系来源"
    )
    
    # 备注
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="备注信息"
    )
    
    # 开始时间
    start_time: Optional[datetime] = Field(
        None,
        description="关系开始时间"
    )
    
    # 结束时间
    end_time: Optional[datetime] = Field(
        None,
        description="关系结束时间"
    )
    
    # 是否为双向关系
    bidirectional: bool = Field(
        default=False,
        description="是否为双向关系"
    )
    
    # 验证器  
    @model_validator(mode='after')
    def validate_verification_consistency(self):
        """验证验证相关字段的一致性"""
        if not self.verified and (self.verified_at or self.verified_by):
            raise ValueError('Cannot set verification details when verified is False')
        return self
    
    @model_validator(mode='after')
    def validate_time_consistency(self):
        """验证时间范围和状态的一致性"""
        # 验证时间范围
        if self.end_time and self.start_time and self.end_time < self.start_time:
            raise ValueError('End time cannot be before start time')
        
        # 根据时间自动调整状态
        if self.status == RelationshipStatus.ACTIVE:
            if self.end_time and self.end_time < datetime.now():
                self.status = RelationshipStatus.INACTIVE
        
        return self
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """
        获取置信度等级
        
        Returns:
            置信度等级枚举值
        """
        return confidence_to_level(self.confidence)
    
    def is_active(self) -> bool:
        """
        判断关系是否活跃
        
        Returns:
            是否为活跃状态
        """
        if self.status != RelationshipStatus.ACTIVE:
            return False
        
        # 检查时间范围
        now = datetime.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        
        return True
    
    def is_verified(self) -> bool:
        """
        判断关系是否已验证
        
        Returns:
            是否已验证
        """
        return self.verified
    
    def verify(self, verified_by: str) -> None:
        """
        验证关系
        
        Args:
            verified_by: 验证者标识
        """
        self.verified = True
        self.verified_at = datetime.now()
        self.verified_by = verified_by
        self.confidence = 1.0  # 验证后置信度设为最高
    
    def calculate_duration(self) -> Optional[float]:
        """
        计算关系持续时间
        
        Returns:
            持续天数，如果无法计算则返回None
        """
        if not self.start_time:
            return None
        
        end = self.end_time or datetime.now()
        duration = end - self.start_time
        return duration.total_seconds() / 86400  # 转换为天数
    
    def to_neo4j(self) -> dict:
        """
        重写父类方法，处理特殊字段
        
        Returns:
            Neo4j属性字典
        """
        data = super().to_neo4j()
        
        # 确保某些字段的格式
        if 'status' in data:
            data['status'] = self.status.value if isinstance(self.status, RelationshipStatus) else self.status
        
        return data
    
    def __repr__(self) -> str:
        """字符串表示"""
        status_str = self.status.value if isinstance(self.status, RelationshipStatus) else self.status
        verified_str = "✓" if self.verified else "✗"
        return f"<{self.__class__.__name__} id={self._id} status={status_str} verified={verified_str} strength={self.strength}>"