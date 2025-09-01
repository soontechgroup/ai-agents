"""
Neomodel 基础模型
"""

from datetime import datetime
from neomodel import (
    StructuredNode,
    StringProperty,
    DateTimeProperty,
    BooleanProperty,
    UniqueIdProperty
)


class BaseNode(StructuredNode):
    """
    所有节点的基类
    提供通用属性和方法
    """
    
    __abstract_node__ = True
    
    # 通用属性
    uid = UniqueIdProperty()
    created_at = DateTimeProperty(default_factory=datetime.now)
    updated_at = DateTimeProperty(default_factory=datetime.now)
    is_active = BooleanProperty(default=True)
    
    def save(self):
        """重写保存方法，自动更新时间戳"""
        self.updated_at = datetime.now()
        return super().save()
    
    def to_dict(self):
        """转换为字典"""
        props = {}
        for key, value in self.__properties__.items():
            val = getattr(self, key)
            if val is not None:
                if isinstance(val, datetime):
                    props[key] = val.isoformat()
                else:
                    props[key] = val
        return props
    
    def update_from_dict(self, data: dict):
        """从字典更新属性"""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['uid', 'created_at']:
                setattr(self, key, value)
        self.save()
        return self
    
    @classmethod
    def find_or_create(cls, **kwargs):
        """查找或创建节点"""
        # 尝试查找
        nodes = cls.nodes.filter(**kwargs)
        if nodes:
            return nodes[0], False
        # 创建新节点
        node = cls(**kwargs)
        node.save()
        return node, True