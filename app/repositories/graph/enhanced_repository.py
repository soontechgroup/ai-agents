"""
增强的图数据库Repository
集成了类型化模型支持
"""

from typing import Dict, List, Any, Optional, Type, TypeVar, Union
from neo4j import Session
import logging

from .base import BaseGraphRepository
from app.models.graph import (
    Node,
    Relationship,
    GraphModelFactory,
    PersonNode,
    OrganizationNode
)

logger = logging.getLogger(__name__)

# 类型变量
TNode = TypeVar('TNode', bound=Node)
TRelationship = TypeVar('TRelationship', bound=Relationship)


class EnhancedGraphRepository(BaseGraphRepository):
    """
    增强的图数据库Repository
    支持类型化的节点和关系模型
    """
    
    def __init__(self, session: Session):
        """
        初始化增强Repository
        
        Args:
            session: Neo4j Session实例
        """
        super().__init__(session)
        self.factory = GraphModelFactory()
    
    # ==================== 节点操作 ====================
    
    def create_typed_node(self, node: Node) -> Node:
        """
        创建类型化节点
        
        Args:
            node: 节点模型实例
        
        Returns:
            带有Neo4j ID的节点实例
        """
        try:
            # 构建标签字符串
            labels = ":".join(node.labels) if node.labels else "Node"
            
            # 构建查询
            query = f"""
            CREATE (n:{labels} $props)
            RETURN n, id(n) as node_id, labels(n) as labels
            """
            
            # 执行查询
            result = self.session.run(query, props=node.to_neo4j())
            record = result.single()
            
            if record:
                # 更新节点的内部ID
                node._id = record["node_id"]
                logger.info(f"Created node: {node}")
                return node
            
            raise Exception("Failed to create node")
            
        except Exception as e:
            logger.error(f"Error creating typed node: {str(e)}")
            raise
    
    def find_node_by_uid(
        self,
        uid: str,
        model_class: Type[TNode] = Node
    ) -> Optional[TNode]:
        """
        根据UID查找节点
        
        Args:
            uid: 节点唯一标识符
            model_class: 节点模型类
        
        Returns:
            节点实例或None
        """
        try:
            query = """
            MATCH (n {uid: $uid})
            RETURN n, id(n) as node_id, labels(n) as labels
            """
            
            result = self.session.run(query, uid=uid)
            record = result.single()
            
            if record:
                # 使用模型类创建实例
                node_data = dict(record["n"])
                return model_class.from_neo4j(
                    node_data,
                    node_id=record["node_id"],
                    labels=record["labels"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding node by uid: {str(e)}")
            return None
    
    def find_nodes_by_label(
        self,
        label: str,
        model_class: Type[TNode] = Node,
        limit: int = 100
    ) -> List[TNode]:
        """
        根据标签查找节点
        
        Args:
            label: 节点标签
            model_class: 节点模型类
            limit: 返回数量限制
        
        Returns:
            节点实例列表
        """
        try:
            query = f"""
            MATCH (n:{label})
            RETURN n, id(n) as node_id, labels(n) as labels
            LIMIT $limit
            """
            
            result = self.session.run(query, limit=limit)
            
            nodes = []
            for record in result:
                node_data = dict(record["n"])
                node = model_class.from_neo4j(
                    node_data,
                    node_id=record["node_id"],
                    labels=record["labels"]
                )
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error finding nodes by label: {str(e)}")
            return []
    
    def update_typed_node(self, node: Node) -> bool:
        """
        更新类型化节点
        
        Args:
            node: 节点模型实例（必须有uid）
        
        Returns:
            是否更新成功
        """
        try:
            query = """
            MATCH (n {uid: $uid})
            SET n += $props
            RETURN n
            """
            
            result = self.session.run(
                query,
                uid=node.uid,
                props=node.to_neo4j()
            )
            
            return result.single() is not None
            
        except Exception as e:
            logger.error(f"Error updating typed node: {str(e)}")
            return False
    
    def delete_typed_node(self, node: Node) -> bool:
        """
        删除类型化节点
        
        Args:
            node: 节点模型实例
        
        Returns:
            是否删除成功
        """
        try:
            query = """
            MATCH (n {uid: $uid})
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            
            result = self.session.run(query, uid=node.uid)
            record = result.single()
            
            return record["deleted_count"] > 0 if record else False
            
        except Exception as e:
            logger.error(f"Error deleting typed node: {str(e)}")
            return False
    
    # ==================== 关系操作 ====================
    
    def create_typed_relationship(
        self,
        from_node: Node,
        to_node: Node,
        relationship: Relationship,
        rel_type: str
    ) -> Relationship:
        """
        创建类型化关系
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
            relationship: 关系模型实例
            rel_type: 关系类型名称
        
        Returns:
            带有Neo4j ID的关系实例
        """
        try:
            query = f"""
            MATCH (a {{uid: $from_uid}}), (b {{uid: $to_uid}})
            CREATE (a)-[r:{rel_type} $props]->(b)
            RETURN r, id(r) as rel_id, type(r) as rel_type
            """
            
            result = self.session.run(
                query,
                from_uid=from_node.uid,
                to_uid=to_node.uid,
                props=relationship.to_neo4j()
            )
            record = result.single()
            
            if record:
                # 更新关系的内部ID
                relationship._id = record["rel_id"]
                
                # 如果是双向关系，创建反向关系
                if relationship.bidirectional:
                    self._create_reverse_relationship(
                        to_node, from_node, relationship, rel_type
                    )
                
                logger.info(f"Created relationship: {rel_type} between {from_node.uid} and {to_node.uid}")
                return relationship
            
            raise Exception("Failed to create relationship")
            
        except Exception as e:
            logger.error(f"Error creating typed relationship: {str(e)}")
            raise
    
    def _create_reverse_relationship(
        self,
        from_node: Node,
        to_node: Node,
        relationship: Relationship,
        rel_type: str
    ) -> None:
        """
        创建反向关系（用于双向关系）
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
            relationship: 关系模型实例
            rel_type: 关系类型名称
        """
        try:
            # 检查是否已存在反向关系
            check_query = f"""
            MATCH (a {{uid: $from_uid}})-[r:{rel_type}]->(b {{uid: $to_uid}})
            RETURN count(r) as count
            """
            
            result = self.session.run(
                check_query,
                from_uid=from_node.uid,
                to_uid=to_node.uid
            )
            record = result.single()
            
            if record and record["count"] == 0:
                # 创建反向关系
                create_query = f"""
                MATCH (a {{uid: $from_uid}}), (b {{uid: $to_uid}})
                CREATE (a)-[r:{rel_type} $props]->(b)
                RETURN r
                """
                
                self.session.run(
                    create_query,
                    from_uid=from_node.uid,
                    to_uid=to_node.uid,
                    props=relationship.to_neo4j()
                )
                
        except Exception as e:
            logger.warning(f"Failed to create reverse relationship: {str(e)}")
    
    def find_relationships_between(
        self,
        from_node: Node,
        to_node: Node,
        rel_type: Optional[str] = None,
        model_class: Type[TRelationship] = Relationship
    ) -> List[TRelationship]:
        """
        查找两个节点之间的关系
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
            rel_type: 关系类型（可选）
            model_class: 关系模型类
        
        Returns:
            关系实例列表
        """
        try:
            if rel_type:
                query = f"""
                MATCH (a {{uid: $from_uid}})-[r:{rel_type}]->(b {{uid: $to_uid}})
                RETURN r, id(r) as rel_id, type(r) as rel_type
                """
            else:
                query = """
                MATCH (a {uid: $from_uid})-[r]->(b {uid: $to_uid})
                RETURN r, id(r) as rel_id, type(r) as rel_type
                """
            
            result = self.session.run(
                query,
                from_uid=from_node.uid,
                to_uid=to_node.uid
            )
            
            relationships = []
            for record in result:
                rel_data = dict(record["r"])
                rel = model_class.from_neo4j(
                    rel_data,
                    rel_id=record["rel_id"]
                )
                relationships.append(rel)
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error finding relationships: {str(e)}")
            return []
    
    def find_connected_nodes(
        self,
        node: Node,
        rel_type: Optional[str] = None,
        direction: str = "both",
        model_class: Type[TNode] = Node,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查找与节点相连的所有节点
        
        Args:
            node: 中心节点
            rel_type: 关系类型（可选）
            direction: 方向（outgoing, incoming, both）
            model_class: 节点模型类
            limit: 返回数量限制
        
        Returns:
            包含节点和关系的字典列表
        """
        try:
            rel_pattern = f":{rel_type}" if rel_type else ""
            
            if direction == "outgoing":
                pattern = f"(a {{uid: $uid}})-[r{rel_pattern}]->(b)"
            elif direction == "incoming":
                pattern = f"(a {{uid: $uid}})<-[r{rel_pattern}]-(b)"
            else:  # both
                pattern = f"(a {{uid: $uid}})-[r{rel_pattern}]-(b)"
            
            query = f"""
            MATCH {pattern}
            RETURN b, id(b) as node_id, labels(b) as labels,
                   r, id(r) as rel_id, type(r) as rel_type
            LIMIT $limit
            """
            
            result = self.session.run(query, uid=node.uid, limit=limit)
            
            connected = []
            for record in result:
                # 创建节点实例
                node_data = dict(record["b"])
                connected_node = self.factory.create_from_neo4j(
                    node_data,
                    labels=record["labels"]
                )
                connected_node._id = record["node_id"]
                
                # 创建关系实例
                rel_data = dict(record["r"])
                relationship = self.factory.create_from_neo4j(
                    rel_data,
                    rel_type=record["rel_type"]
                )
                relationship._id = record["rel_id"]
                
                connected.append({
                    "node": connected_node,
                    "relationship": relationship
                })
            
            return connected
            
        except Exception as e:
            logger.error(f"Error finding connected nodes: {str(e)}")
            return []
    
    # ==================== 批量操作 ====================
    
    def batch_create_nodes(self, nodes: List[Node]) -> List[Node]:
        """
        批量创建节点
        
        Args:
            nodes: 节点列表
        
        Returns:
            创建成功的节点列表
        """
        created = []
        for node in nodes:
            try:
                created_node = self.create_typed_node(node)
                created.append(created_node)
            except Exception as e:
                logger.error(f"Failed to create node {node.uid}: {str(e)}")
        
        return created
    
    def batch_create_relationships(
        self,
        relationships: List[tuple[Node, Node, Relationship, str]]
    ) -> List[Relationship]:
        """
        批量创建关系
        
        Args:
            relationships: (from_node, to_node, relationship, rel_type) 元组列表
        
        Returns:
            创建成功的关系列表
        """
        created = []
        for from_node, to_node, rel, rel_type in relationships:
            try:
                created_rel = self.create_typed_relationship(
                    from_node, to_node, rel, rel_type
                )
                created.append(created_rel)
            except Exception as e:
                logger.error(f"Failed to create relationship: {str(e)}")
        
        return created
    
    # ==================== 高级查询 ====================
    
    def find_path(
        self,
        from_node: Node,
        to_node: Node,
        max_depth: int = 5,
        rel_types: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查找两个节点之间的路径
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
            max_depth: 最大深度
            rel_types: 允许的关系类型
        
        Returns:
            路径信息
        """
        try:
            if rel_types:
                rel_pattern = "|".join(rel_types)
                rel_filter = f"[:{rel_pattern}*1..{max_depth}]"
            else:
                rel_filter = f"[*1..{max_depth}]"
            
            query = f"""
            MATCH path = shortestPath((a {{uid: $from_uid}})-{rel_filter}-(b {{uid: $to_uid}}))
            RETURN path, length(path) as path_length
            """
            
            result = self.session.run(
                query,
                from_uid=from_node.uid,
                to_uid=to_node.uid
            )
            record = result.single()
            
            if record:
                path = record["path"]
                return {
                    "length": record["path_length"],
                    "nodes": [dict(node) for node in path.nodes],
                    "relationships": [dict(rel) for rel in path.relationships]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding path: {str(e)}")
            return None