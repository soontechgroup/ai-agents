from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class DynamicRelationship(BaseModel):
    
    uid: str = Field(default_factory=lambda: uuid.uuid4().hex, description="关系唯一标识")
    source_name: str = Field(..., description="源实体名称")
    target_name: str = Field(..., description="目标实体名称")
    
    relationship_types: List[str] = Field(default_factory=list, description="关系类型列表，可以有多种")
    properties: Dict[str, Any] = Field(default_factory=dict, description="动态属性")
    contexts: List[Dict[str, Any]] = Field(default_factory=list, description="不同上下文中的关系表现")
    
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="关系置信度")
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="关系强度")
    
    bidirectional: bool = Field(default=False, description="是否双向关系")
    temporal_aspects: List[Dict[str, Any]] = Field(default_factory=list, description="关系的时间演化")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    valid_from: Optional[datetime] = Field(None, description="关系开始时间")
    valid_until: Optional[datetime] = Field(None, description="关系结束时间")
    
    def add_type(self, rel_type: str) -> None:
        if rel_type not in self.relationship_types:
            self.relationship_types.append(rel_type)
            self.updated_at = datetime.now()
    
    def set_property(self, key: str, value: Any) -> None:
        self.properties[key] = value
        self.updated_at = datetime.now()
    
    def add_context(self, context: Dict[str, Any], timestamp: datetime = None) -> None:
        context_entry = {
            "timestamp": (timestamp or datetime.now()).isoformat(),
            "data": context
        }
        self.contexts.append(context_entry)
        self.updated_at = datetime.now()
    
    def record_temporal_change(self, aspect: str, old_value: Any, new_value: Any) -> None:
        change = {
            "timestamp": datetime.now().isoformat(),
            "aspect": aspect,
            "old_value": old_value,
            "new_value": new_value
        }
        self.temporal_aspects.append(change)
    
    def is_active(self, at_time: datetime = None) -> bool:
        check_time = at_time or datetime.now()
        
        if self.valid_from and check_time < self.valid_from:
            return False
        if self.valid_until and check_time > self.valid_until:
            return False
        
        return True
    
    def merge_with(self, other: 'DynamicRelationship') -> None:
        for rel_type in other.relationship_types:
            self.add_type(rel_type)
        
        for key, value in other.properties.items():
            if key not in self.properties:
                self.set_property(key, value)
        
        self.contexts.extend(other.contexts)
        self.temporal_aspects.extend(other.temporal_aspects)
        
        self.confidence = max(self.confidence, other.confidence)
        self.strength = max(self.strength, other.strength)
        
        if other.valid_from and (not self.valid_from or other.valid_from < self.valid_from):
            self.valid_from = other.valid_from
        
        if other.valid_until and (not self.valid_until or other.valid_until > self.valid_until):
            self.valid_until = other.valid_until
        
        self.updated_at = datetime.now()
    
    def to_cypher_format(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "types": self.relationship_types,
            "properties": self.properties,
            "confidence": self.confidence,
            "strength": self.strength,
            "bidirectional": self.bidirectional,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def get_primary_type(self) -> Optional[str]:
        return self.relationship_types[0] if self.relationship_types else None
    
    def has_type(self, rel_type: str) -> bool:
        return rel_type.lower() in [t.lower() for t in self.relationship_types]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }