"""
动态实体模型
基于 GraphRAG 理念的通用实体表示
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class DynamicEntity(BaseModel):
    """
    动态实体 - 不预设任何领域特定结构
    让 AI 从数据中发现实体的属性和关系
    """
    
    # 核心标识（仅这些是必需的）
    uid: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str = Field(..., description="实体名称")
    
    # 动态类型（可以同时属于多个类型）
    types: List[str] = Field(
        default_factory=list,
        description="实体类型列表，由 AI 推断"
    )
    
    # 完全动态的属性存储
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="动态属性，不限定字段"
    )
    
    # 描述信息（由 AI 生成）
    description: Optional[str] = Field(
        None,
        description="实体描述，由 AI 从上下文生成"
    )
    
    # 上下文信息（保留不同语境下的表现）
    contexts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="实体在不同上下文中的信息"
    )
    
    # 来源追踪
    sources: List[str] = Field(
        default_factory=list,
        description="信息来源"
    )
    
    # 置信度（AI 对信息的确定性）
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="整体置信度分数"
    )
    
    # 属性级置信度
    property_confidence: Dict[str, float] = Field(
        default_factory=dict,
        description="每个属性的置信度"
    )
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 时间演化（记录属性如何随时间变化）
    temporal_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="属性的时间变化记录"
    )
    
    def add_type(self, entity_type: str) -> None:
        """添加新的类型标签"""
        if entity_type not in self.types:
            self.types.append(entity_type)
            self.updated_at = datetime.now()
    
    def set_property(self, key: str, value: Any, confidence: float = 0.5) -> None:
        """设置动态属性"""
        self.properties[key] = value
        self.property_confidence[key] = confidence
        self.updated_at = datetime.now()
    
    def add_context(self, context: Dict[str, Any], source: str) -> None:
        """添加新的上下文信息"""
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "data": context
        }
        self.contexts.append(context_entry)
        if source not in self.sources:
            self.sources.append(source)
        self.updated_at = datetime.now()
    
    def record_change(self, property_name: str, old_value: Any, new_value: Any) -> None:
        """记录属性变化"""
        change = {
            "timestamp": datetime.now().isoformat(),
            "property": property_name,
            "old_value": old_value,
            "new_value": new_value
        }
        self.temporal_changes.append(change)
    
    def merge_with(self, other: 'DynamicEntity') -> None:
        """合并另一个实体的信息"""
        # 合并类型
        for t in other.types:
            self.add_type(t)
        
        # 合并属性（选择置信度更高的）
        for key, value in other.properties.items():
            other_confidence = other.property_confidence.get(key, 0.5)
            current_confidence = self.property_confidence.get(key, 0)
            
            if other_confidence > current_confidence:
                old_value = self.properties.get(key)
                self.set_property(key, value, other_confidence)
                if old_value is not None and old_value != value:
                    self.record_change(key, old_value, value)
        
        # 合并上下文
        self.contexts.extend(other.contexts)
        
        # 合并来源
        for source in other.sources:
            if source not in self.sources:
                self.sources.append(source)
        
        # 更新整体置信度
        self.confidence = max(self.confidence, other.confidence)
        self.updated_at = datetime.now()
    
    def to_graph_format(self) -> Dict[str, Any]:
        """转换为图数据库存储格式"""
        return {
            "uid": self.uid,
            "name": self.name,
            "types": self.types,
            "description": self.description,
            "properties": self.properties,
            "confidence": self.confidence,
            "sources": self.sources,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def get_property_with_confidence(self, key: str) -> tuple[Any, float]:
        """获取属性值及其置信度"""
        value = self.properties.get(key)
        confidence = self.property_confidence.get(key, 0.0)
        return value, confidence
    
    def has_type(self, entity_type: str) -> bool:
        """检查是否包含特定类型"""
        return entity_type.lower() in [t.lower() for t in self.types]
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取实体演化摘要"""
        return {
            "entity_name": self.name,
            "current_types": self.types,
            "property_count": len(self.properties),
            "context_count": len(self.contexts),
            "change_count": len(self.temporal_changes),
            "source_count": len(self.sources),
            "confidence": self.confidence,
            "last_updated": self.updated_at.isoformat()
        }
    
    class Config:
        """Pydantic 配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }