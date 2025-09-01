"""
图数据库模型基础类
提供节点和关系的抽象基类
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, TypeVar, Type, TYPE_CHECKING
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.converters.graph_converter import GraphModelConverter


class GraphEntity(BaseModel, ABC):
    """
    图数据库实体基类
    所有节点和关系的共同基类
    """
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="更新时间"
    )
    
    class Config:
        # 允许额外字段以保持Neo4j的灵活性
        extra = "allow"
        # 使用枚举值而不是枚举对象
        use_enum_values = True
        # JSON序列化配置
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        # 允许字段赋值验证
        validate_assignment = True
    
    @abstractmethod
    def to_neo4j(self) -> Dict[str, Any]:
        """
        转换为Neo4j存储格式
        
        Returns:
            适合Neo4j存储的属性字典
        """
        pass
    
    @classmethod
    @abstractmethod
    def from_neo4j(cls, data: Dict[str, Any], **kwargs):
        """
        从Neo4j数据创建实例
        
        Args:
            data: Neo4j返回的属性字典
            **kwargs: 额外参数（如node_id, labels等）
        
        Returns:
            模型实例
        """
        pass
    
    def dict_for_neo4j(self) -> Dict[str, Any]:
        """
        获取适合Neo4j存储的字典（辅助方法）
        
        Returns:
            处理后的属性字典
        """
        data = self.dict(exclude_none=True)
        # 转换datetime为字符串
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, list):
                # 处理列表类型，确保可序列化
                data[key] = [
                    v.isoformat() if isinstance(v, datetime) else v
                    for v in value
                ]
        return data
    
    def to_neomodel(self):
        """
        转换为Neomodel实例
        
        Returns:
            对应的Neomodel模型实例
        """
        from app.models.converters.graph_converter import GraphModelConverter
        return GraphModelConverter.pydantic_to_neomodel(self)
    
    @classmethod
    def from_neomodel(cls, neomodel_obj):
        """
        从Neomodel实例创建Pydantic模型
        
        Args:
            neomodel_obj: Neomodel模型实例
        
        Returns:
            对应的Pydantic模型实例
        """
        from app.models.converters.graph_converter import GraphModelConverter
        return GraphModelConverter.neomodel_to_pydantic(neomodel_obj)


class Node(GraphEntity):
    """
    节点基类
    所有节点类型的基类
    """
    
    # Neo4j内部ID（查询后填充，不参与序列化）
    _id: Optional[int] = None
    
    # 业务唯一标识符（必须唯一）
    uid: Optional[str] = Field(
        None,
        description="唯一标识符",
        min_length=1,
        max_length=100
    )
    
    # 节点标签（可以有多个）
    labels: List[str] = Field(
        default_factory=list,
        description="节点标签列表"
    )
    
    def to_neo4j(self) -> Dict[str, Any]:
        """
        转换为Neo4j属性字典
        
        Returns:
            不包含内部字段的属性字典
        """
        # 排除内部字段和标签
        exclude_fields = {'_id', 'labels'}
        data = self.dict(exclude=exclude_fields, exclude_none=True)
        
        # 处理datetime类型
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, list):
                data[key] = [
                    v.isoformat() if isinstance(v, datetime) else v
                    for v in value
                ]
        
        return data
    
    @classmethod
    def from_neo4j(
        cls,
        data: Dict[str, Any],
        node_id: Optional[int] = None,
        labels: Optional[List[str]] = None
    ):
        """
        从Neo4j记录创建节点实例
        
        Args:
            data: 节点属性字典
            node_id: Neo4j内部节点ID
            labels: 节点标签列表
        
        Returns:
            节点实例
        """
        # 处理datetime字符串
        for key, value in data.items():
            if isinstance(value, str):
                # 尝试解析ISO格式的datetime
                if 'T' in value and ('+' in value or 'Z' in value or value.count(':') >= 2):
                    try:
                        data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
        
        instance = cls(**data)
        instance._id = node_id
        if labels:
            instance.labels = labels
        
        return instance
    
    def add_label(self, label: str) -> None:
        """
        添加标签
        
        Args:
            label: 要添加的标签
        """
        if label not in self.labels:
            self.labels.append(label)
    
    def remove_label(self, label: str) -> None:
        """
        移除标签
        
        Args:
            label: 要移除的标签
        """
        if label in self.labels:
            self.labels.remove(label)
    
    def has_label(self, label: str) -> bool:
        """
        检查是否有某个标签
        
        Args:
            label: 要检查的标签
        
        Returns:
            是否包含该标签
        """
        return label in self.labels
    
    @property
    def node_id(self) -> Optional[int]:
        """获取Neo4j内部ID"""
        return self._id
    
    def __repr__(self) -> str:
        """字符串表示"""
        labels_str = ":".join(self.labels) if self.labels else "Node"
        return f"<{labels_str} uid='{self.uid}' id={self._id}>"


class Relationship(GraphEntity):
    """
    关系基类
    所有关系类型的基类
    """
    
    # Neo4j内部ID（查询后填充）
    _id: Optional[int] = None
    
    # 关系强度（0-1之间，用于表示关系的紧密程度）
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="关系强度"
    )
    
    # 关系权重（用于图算法，如最短路径）
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="关系权重"
    )
    
    # 置信度（表示关系的确定性）
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="置信度"
    )
    
    def to_neo4j(self) -> Dict[str, Any]:
        """
        转换为Neo4j属性字典
        
        Returns:
            不包含内部字段的属性字典
        """
        # 排除内部ID
        data = self.dict(exclude={'_id'}, exclude_none=True)
        
        # 处理datetime类型
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, list):
                data[key] = [
                    v.isoformat() if isinstance(v, datetime) else v
                    for v in value
                ]
        
        return data
    
    @classmethod
    def from_neo4j(
        cls,
        data: Dict[str, Any],
        rel_id: Optional[int] = None
    ):
        """
        从Neo4j记录创建关系实例
        
        Args:
            data: 关系属性字典
            rel_id: Neo4j内部关系ID
        
        Returns:
            关系实例
        """
        # 处理datetime字符串
        for key, value in data.items():
            if isinstance(value, str):
                # 尝试解析ISO格式的datetime
                if 'T' in value and ('+' in value or 'Z' in value or value.count(':') >= 2):
                    try:
                        data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
        
        instance = cls(**data)
        instance._id = rel_id
        
        return instance
    
    @property
    def relationship_id(self) -> Optional[int]:
        """获取Neo4j内部ID"""
        return self._id
    
    def inverse_strength(self) -> float:
        """
        获取反向强度（用于某些算法）
        
        Returns:
            1 - strength
        """
        return 1.0 - self.strength
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Relationship id={self._id} strength={self.strength}>"


# 类型变量，用于泛型
TNode = TypeVar('TNode', bound=Node)
TRelationship = TypeVar('TRelationship', bound=Relationship)