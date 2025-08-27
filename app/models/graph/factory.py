"""
图模型工厂
提供动态创建节点和关系的功能
"""

from typing import Dict, Any, Type, Optional, Union
from importlib import import_module
import logging

from app.models.graph.base import Node, Relationship
from app.models.graph.nodes import PersonNode
from app.models.graph.nodes.organization import OrganizationNode
from app.models.graph.relationships import (
    BaseRelationship,
    FriendRelationship,
    FamilyRelationship,
    KnowsRelationship,
    WorksAtRelationship,
    ColleagueRelationship,
    MentorshipRelationship,
    BusinessPartnershipRelationship
)

logger = logging.getLogger(__name__)


class GraphModelFactory:
    """
    图模型工厂类
    用于动态创建节点和关系实例
    """
    
    # 注册的节点模型
    _node_models: Dict[str, Type[Node]] = {
        "Person": PersonNode,
        "PersonNode": PersonNode,
        "Organization": OrganizationNode,
        "OrganizationNode": OrganizationNode,
    }
    
    # 注册的关系模型
    _relationship_models: Dict[str, Type[Relationship]] = {
        # 基础关系
        "BASE": BaseRelationship,
        "BaseRelationship": BaseRelationship,
        
        # 社交关系
        "FRIEND": FriendRelationship,
        "FriendRelationship": FriendRelationship,
        "FAMILY": FamilyRelationship,
        "FamilyRelationship": FamilyRelationship,
        "KNOWS": KnowsRelationship,
        "KnowsRelationship": KnowsRelationship,
        
        # 职业关系
        "WORKS_AT": WorksAtRelationship,
        "WorksAtRelationship": WorksAtRelationship,
        "COLLEAGUE": ColleagueRelationship,
        "ColleagueRelationship": ColleagueRelationship,
        "MENTORSHIP": MentorshipRelationship,
        "MentorshipRelationship": MentorshipRelationship,
        "BUSINESS_PARTNER": BusinessPartnershipRelationship,
        "BusinessPartnershipRelationship": BusinessPartnershipRelationship,
    }
    
    @classmethod
    def create_node(cls, node_type: str, **kwargs) -> Node:
        """
        创建节点实例
        
        Args:
            node_type: 节点类型名称
            **kwargs: 节点属性
        
        Returns:
            节点实例
        
        Raises:
            ValueError: 如果节点类型未注册
        """
        # 查找节点模型
        model_class = cls._node_models.get(node_type)
        
        if not model_class:
            # 尝试动态导入
            model_class = cls._try_import_node_model(node_type)
            if not model_class:
                raise ValueError(f"Unknown node type: {node_type}")
        
        try:
            return model_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create node of type {node_type}: {str(e)}")
            raise
    
    @classmethod
    def create_relationship(cls, rel_type: str, **kwargs) -> Relationship:
        """
        创建关系实例
        
        Args:
            rel_type: 关系类型名称
            **kwargs: 关系属性
        
        Returns:
            关系实例
        
        Raises:
            ValueError: 如果关系类型未注册
        """
        # 查找关系模型
        model_class = cls._relationship_models.get(rel_type)
        
        if not model_class:
            # 尝试动态导入
            model_class = cls._try_import_relationship_model(rel_type)
            if not model_class:
                # 如果找不到具体模型，使用基础关系模型
                logger.warning(f"Unknown relationship type: {rel_type}, using BaseRelationship")
                model_class = BaseRelationship
        
        try:
            return model_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create relationship of type {rel_type}: {str(e)}")
            raise
    
    @classmethod
    def register_node_model(cls, name: str, model_class: Type[Node]) -> None:
        """
        注册节点模型
        
        Args:
            name: 模型名称
            model_class: 模型类
        """
        if not issubclass(model_class, Node):
            raise TypeError(f"{model_class} must be a subclass of Node")
        
        cls._node_models[name] = model_class
        logger.info(f"Registered node model: {name} -> {model_class.__name__}")
    
    @classmethod
    def register_relationship_model(cls, name: str, model_class: Type[Relationship]) -> None:
        """
        注册关系模型
        
        Args:
            name: 模型名称
            model_class: 模型类
        """
        if not issubclass(model_class, Relationship):
            raise TypeError(f"{model_class} must be a subclass of Relationship")
        
        cls._relationship_models[name] = model_class
        logger.info(f"Registered relationship model: {name} -> {model_class.__name__}")
    
    @classmethod
    def get_node_models(cls) -> Dict[str, Type[Node]]:
        """
        获取所有注册的节点模型
        
        Returns:
            节点模型字典
        """
        return cls._node_models.copy()
    
    @classmethod
    def get_relationship_models(cls) -> Dict[str, Type[Relationship]]:
        """
        获取所有注册的关系模型
        
        Returns:
            关系模型字典
        """
        return cls._relationship_models.copy()
    
    @classmethod
    def _try_import_node_model(cls, node_type: str) -> Optional[Type[Node]]:
        """
        尝试动态导入节点模型
        
        Args:
            node_type: 节点类型名称
        
        Returns:
            模型类或None
        """
        # 转换为模块名（如：Location -> location）
        module_name = node_type.lower().replace('node', '')
        
        try:
            # 尝试导入模块
            module = import_module(f".nodes.{module_name}", package="app.models.graph")
            
            # 查找模型类
            # 尝试几种可能的类名
            possible_names = [
                f"{node_type}Node",
                f"{node_type}",
                f"{module_name.capitalize()}Node"
            ]
            
            for name in possible_names:
                if hasattr(module, name):
                    model_class = getattr(module, name)
                    if issubclass(model_class, Node):
                        # 注册到缓存
                        cls._node_models[node_type] = model_class
                        return model_class
        except ImportError:
            pass
        
        return None
    
    @classmethod
    def _try_import_relationship_model(cls, rel_type: str) -> Optional[Type[Relationship]]:
        """
        尝试动态导入关系模型
        
        Args:
            rel_type: 关系类型名称
        
        Returns:
            模型类或None
        """
        # 关系类型通常使用下划线分隔，转换为驼峰命名
        # 如：WORKS_AT -> WorksAt
        class_name = ''.join(word.capitalize() for word in rel_type.split('_'))
        class_name += 'Relationship'
        
        # 尝试从不同的模块导入
        modules_to_try = [
            "social",
            "professional",
            "economic",
            "spatial",
            "temporal"
        ]
        
        for module_name in modules_to_try:
            try:
                module = import_module(f".relationships.{module_name}", package="app.models.graph")
                if hasattr(module, class_name):
                    model_class = getattr(module, class_name)
                    if issubclass(model_class, Relationship):
                        # 注册到缓存
                        cls._relationship_models[rel_type] = model_class
                        return model_class
            except ImportError:
                continue
        
        return None
    
    @classmethod
    def create_from_neo4j(
        cls,
        data: Dict[str, Any],
        labels: Optional[list] = None,
        rel_type: Optional[str] = None
    ) -> Union[Node, Relationship]:
        """
        从Neo4j数据创建模型实例
        
        Args:
            data: Neo4j返回的数据
            labels: 节点标签（用于判断节点类型）
            rel_type: 关系类型（用于判断关系类型）
        
        Returns:
            节点或关系实例
        """
        if labels:
            # 创建节点
            # 根据标签确定节点类型
            for label in labels:
                if label in cls._node_models:
                    model_class = cls._node_models[label]
                    return model_class.from_neo4j(data, labels=labels)
            
            # 如果没有找到对应模型，使用第一个标签尝试
            if labels:
                try:
                    return cls.create_node(labels[0], **data)
                except:
                    # 创建通用节点
                    node = Node(**data)
                    node.labels = labels
                    return node
        
        elif rel_type:
            # 创建关系
            if rel_type in cls._relationship_models:
                model_class = cls._relationship_models[rel_type]
                return model_class.from_neo4j(data)
            else:
                return cls.create_relationship(rel_type, **data)
        
        raise ValueError("Cannot determine model type from data")


# 工厂方法快捷方式
def create_node(node_type: str, **kwargs) -> Node:
    """创建节点的快捷方法"""
    return GraphModelFactory.create_node(node_type, **kwargs)


def create_relationship(rel_type: str, **kwargs) -> Relationship:
    """创建关系的快捷方法"""
    return GraphModelFactory.create_relationship(rel_type, **kwargs)


def register_node(name: str, model_class: Type[Node]) -> None:
    """注册节点模型的快捷方法"""
    GraphModelFactory.register_node_model(name, model_class)


def register_relationship(name: str, model_class: Type[Relationship]) -> None:
    """注册关系模型的快捷方法"""
    GraphModelFactory.register_relationship_model(name, model_class)