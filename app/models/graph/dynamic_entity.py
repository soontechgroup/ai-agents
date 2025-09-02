from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class DynamicEntity(BaseModel):
    
    uid: str = Field(default_factory=lambda: uuid.uuid4().hex, description="唯一标识符")
    name: str = Field(..., description="实体名称")
    
    types: List[str] = Field(default_factory=list, description="实体类型列表，由 AI 推断")
    properties: Dict[str, Any] = Field(default_factory=dict, description="动态属性，不限定字段")
    description: Optional[str] = Field(None, description="实体描述")
    contexts: List[Dict[str, Any]] = Field(default_factory=list, description="不同上下文中的信息")
    sources: List[str] = Field(default_factory=list, description="信息来源")
    
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="整体置信度分数")
    property_confidence: Dict[str, float] = Field(default_factory=dict, description="每个属性的置信度")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    temporal_changes: List[Dict[str, Any]] = Field(default_factory=list, description="属性的时间变化记录")
    
    def add_type(self, entity_type: str) -> None:
        if entity_type not in self.types:
            self.types.append(entity_type)
            self.updated_at = datetime.now()
    
    def set_property(self, key: str, value: Any, confidence: float = 0.5) -> None:
        self.properties[key] = value
        self.property_confidence[key] = confidence
        self.updated_at = datetime.now()
    
    def add_context(self, context: Dict[str, Any], source: str) -> None:
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
        change = {
            "timestamp": datetime.now().isoformat(),
            "property": property_name,
            "old_value": old_value,
            "new_value": new_value
        }
        self.temporal_changes.append(change)
    
    def merge_with(self, other: 'DynamicEntity') -> None:
        for t in other.types:
            self.add_type(t)
        
        for key, value in other.properties.items():
            other_confidence = other.property_confidence.get(key, 0.5)
            current_confidence = self.property_confidence.get(key, 0)
            
            if other_confidence > current_confidence:
                old_value = self.properties.get(key)
                self.set_property(key, value, other_confidence)
                if old_value is not None and old_value != value:
                    self.record_change(key, old_value, value)
        
        self.contexts.extend(other.contexts)
        
        for source in other.sources:
            if source not in self.sources:
                self.sources.append(source)
        
        self.confidence = max(self.confidence, other.confidence)
        self.updated_at = datetime.now()
    
    def to_graph_format(self) -> Dict[str, Any]:
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
        value = self.properties.get(key)
        confidence = self.property_confidence.get(key, 0.0)
        return value, confidence
    
    def has_type(self, entity_type: str) -> bool:
        return entity_type.lower() in [t.lower() for t in self.types]
    
    def get_evolution_summary(self) -> Dict[str, Any]:
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
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }