"""
图数据库统一操作接口
"""

from typing import Dict, List, Any, Optional, Union
from neo4j import Session
from .node_repository import GraphNodeRepository
from .relationship_repository import GraphRelationshipRepository
import logging

logger = logging.getLogger(__name__)


class GraphRepository:
    """统一的图数据库操作接口"""
    
    def __init__(self, session: Session):
        self.session = session
        self.nodes = GraphNodeRepository(session)
        self.relationships = GraphRelationshipRepository(session)
    
    # ==================== 便捷的组合操作 ====================
    
    def create_node_with_relationships(
        self,
        label: str,
        properties: Dict[str, Any],
        connections: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建节点并同时建立多个关系"""
        try:
            # 创建节点
            node = self.nodes.create(label, properties)
            
            # 建立关系
            if connections:
                created_relationships = []
                for conn in connections:
                    direction = conn.get('direction', 'to')
                    rel_properties = conn.get('properties', {})
                    
                    if direction == 'from':
                        # 从其他节点指向新节点
                        rel = self.relationships.create(
                            conn['from_id'],
                            node['id'],
                            conn['type'],
                            rel_properties
                        )
                    else:
                        # 从新节点指向其他节点
                        rel = self.relationships.create(
                            node['id'],
                            conn['to_id'],
                            conn['type'],
                            rel_properties
                        )
                    
                    if rel:
                        created_relationships.append(rel)
                
                node['relationships'] = created_relationships
            
            return node
            
        except Exception as e:
            logger.error(f"创建节点及关系失败: {str(e)}")
            raise
    
    def find_node_with_connections(
        self,
        node_id: int,
        rel_type: Optional[str] = None,
        direction: str = "both"
    ) -> Optional[Dict[str, Any]]:
        """获取节点及其所有连接信息"""
        node = self.nodes.find_by_id(node_id)
        if not node:
            return None
        
        # 获取连接信息
        connections = self.relationships.find_connected_nodes(
            node_id, rel_type, direction
        )
        
        node['connections'] = connections
        node['connection_count'] = len(connections)
        
        return node
    
    def delete_node_cascade(self, node_id: int) -> bool:
        """级联删除节点"""
        return self.nodes.delete(node_id)
    
    def create_nodes_batch(
        self,
        nodes_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量创建节点"""
        created_nodes = []
        for node_data in nodes_data:
            node = self.nodes.create(
                node_data['label'],
                node_data['properties']
            )
            if node:
                created_nodes.append(node)
        
        return created_nodes
    
    def create_relationships_batch(
        self,
        relationships_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量创建关系"""
        created_relationships = []
        for rel_data in relationships_data:
            rel = self.relationships.create(
                rel_data['from_id'],
                rel_data['to_id'],
                rel_data['type'],
                rel_data.get('properties', {})
            )
            if rel:
                created_relationships.append(rel)
        
        return created_relationships
    
    def find_or_create_node(
        self,
        label: str,
        unique_property: str,
        unique_value: Any,
        properties: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """查找或创建节点（基于唯一属性）"""
        # 先尝试查找
        existing = self.nodes.find_by_property(label, unique_property, unique_value)
        if existing:
            return existing
        
        # 不存在则创建
        if properties is None:
            properties = {}
        properties[unique_property] = unique_value
        
        return self.nodes.create(label, properties)
    
    def update_node_and_relationships(
        self,
        node_id: int,
        node_properties: Dict[str, Any] = None,
        relationship_updates: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """同时更新节点和其关系"""
        # 更新节点
        if node_properties:
            node = self.nodes.update(node_id, node_properties)
        else:
            node = self.nodes.find_by_id(node_id)
        
        if not node:
            return None
        
        # 更新关系
        if relationship_updates:
            updated_relationships = []
            for rel_update in relationship_updates:
                rel = self.relationships.update(
                    rel_update['rel_id'],
                    rel_update['properties']
                )
                if rel:
                    updated_relationships.append(rel)
            
            node['updated_relationships'] = updated_relationships
        
        return node
    
    def clone_node(
        self,
        node_id: int,
        new_properties: Dict[str, Any] = None,
        clone_relationships: bool = False
    ) -> Optional[Dict[str, Any]]:
        """克隆节点"""
        # 获取原节点
        original = self.nodes.find_by_id(node_id)
        if not original:
            return None
        
        # 准备新节点属性
        properties = original['properties'].copy()
        if new_properties:
            properties.update(new_properties)
        
        # 创建新节点
        new_node = self.nodes.create(
            original['labels'][0] if original.get('labels') else 'Node',
            properties
        )
        
        # 克隆关系
        if clone_relationships and new_node:
            # 获取原节点的所有关系
            connections = self.relationships.find_connected_nodes(node_id)
            
            for conn in connections:
                # 根据关系方向创建新关系
                # 这里简化处理，实际可能需要更复杂的逻辑
                rel_info = conn['relationship']
                if rel_info:
                    self.relationships.create(
                        new_node['id'],
                        conn['node']['id'],
                        rel_info['type'],
                        rel_info.get('properties', {})
                    )
        
        return new_node
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图数据库统计信息"""
        return {
            'total_nodes': self.nodes.count(),
            'total_relationships': self.relationships.count(),
            'node_labels': {
                # 可以扩展为动态获取所有标签的统计
                'User': self.nodes.count('User'),
                'DigitalHuman': self.nodes.count('DigitalHuman'),
                'Conversation': self.nodes.count('Conversation'),
                'Message': self.nodes.count('Message')
            }
        }
    
    def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行自定义 Cypher 查询"""
        return self.nodes.execute_query(query, parameters)