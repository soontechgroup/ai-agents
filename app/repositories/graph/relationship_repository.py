"""图关系操作 Repository"""

from typing import Dict, List, Any, Optional
from .base import BaseGraphRepository
import logging

logger = logging.getLogger(__name__)


class GraphRelationshipRepository(BaseGraphRepository):
    """关系操作 Repository"""
    
    def create(
        self,
        from_node_id: int,
        to_node_id: int,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """创建两个节点之间的关系"""
        props = properties or {}
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:{rel_type} $props]->(b)
        RETURN r, id(r) as rel_id, type(r) as rel_type
        """
        
        result = self.session.run(
            query,
            from_id=from_node_id,
            to_id=to_node_id,
            props=props
        )
        record = result.single()
        
        if record:
            return {
                "id": record["rel_id"],
                "type": record["rel_type"],
                "properties": dict(record["r"]),
                "from_node_id": from_node_id,
                "to_node_id": to_node_id
            }
        return None
    
    def find_by_nodes(
        self,
        from_node_id: int,
        to_node_id: int,
        rel_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """查找两个节点之间的关系"""
        if rel_type:
            query = f"""
            MATCH (a)-[r:{rel_type}]->(b)
            WHERE id(a) = $from_id AND id(b) = $to_id
            RETURN r, id(r) as rel_id, type(r) as rel_type
            """
        else:
            query = """
            MATCH (a)-[r]->(b)
            WHERE id(a) = $from_id AND id(b) = $to_id
            RETURN r, id(r) as rel_id, type(r) as rel_type
            """
        
        result = self.session.run(query, from_id=from_node_id, to_id=to_node_id)
        
        relationships = []
        for record in result:
            relationships.append({
                "id": record["rel_id"],
                "type": record["rel_type"],
                "properties": dict(record["r"]),
                "from_node_id": from_node_id,
                "to_node_id": to_node_id
            })
        
        return relationships
    
    def find_connected_nodes(
        self,
        node_id: int,
        rel_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """查找与某个节点相连的所有节点"""
        rel_pattern = f":{rel_type}" if rel_type else ""
        
        if direction == "outgoing":
            pattern = f"(a)-[r{rel_pattern}]->(b)"
        elif direction == "incoming":
            pattern = f"(a)<-[r{rel_pattern}]-(b)"
        else:  # both
            pattern = f"(a)-[r{rel_pattern}]-(b)"
        
        query = f"""
        MATCH {pattern}
        WHERE id(a) = $node_id
        RETURN b, id(b) as node_id, labels(b) as labels,
               r, id(r) as rel_id, type(r) as rel_type
        """
        
        result = self.session.run(query, node_id=node_id)
        
        nodes = []
        for record in result:
            nodes.append({
                "node": {
                    "id": record["node_id"],
                    "labels": record["labels"],
                    "properties": dict(record["b"])
                },
                "relationship": {
                    "id": record["rel_id"],
                    "type": record["rel_type"],
                    "properties": dict(record["r"])
                }
            })
        
        return nodes
    
    def find_shortest_path(
        self,
        from_node_id: int,
        to_node_id: int,
        rel_types: Optional[List[str]] = None,
        max_hops: int = 10
    ) -> Optional[Dict[str, Any]]:
        """查找两个节点之间的最短路径"""
        if rel_types:
            rel_pattern = "|".join(rel_types)
            rel_filter = f"[:{rel_pattern}*..{max_hops}]"
        else:
            rel_filter = f"[*..{max_hops}]"
        
        query = f"""
        MATCH path = shortestPath((a)-{rel_filter}-(b))
        WHERE id(a) = $from_id AND id(b) = $to_id
        RETURN path, length(path) as path_length
        """
        
        result = self.session.run(query, from_id=from_node_id, to_id=to_node_id)
        record = result.single()
        
        if record:
            path = record["path"]
            return {
                "length": record["path_length"],
                "nodes": [{"id": node.id, "properties": dict(node)} for node in path.nodes],
                "relationships": [
                    {"type": rel.type, "properties": dict(rel)}
                    for rel in path.relationships
                ]
            }
        return None
    
    def update(self, rel_id: int, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新关系属性"""
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        SET r += $props
        RETURN r, id(r) as rel_id, type(r) as rel_type
        """
        
        result = self.session.run(query, rel_id=rel_id, props=properties)
        record = result.single()
        
        if record:
            return {
                "id": record["rel_id"],
                "type": record["rel_type"],
                "properties": dict(record["r"])
            }
        return None
    
    def delete(self, rel_id: int) -> bool:
        """删除关系"""
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        DELETE r
        RETURN count(r) as deleted_count
        """
        
        result = self.session.run(query, rel_id=rel_id)
        record = result.single()
        
        return record["deleted_count"] > 0 if record else False
    
    def delete_between_nodes(
        self,
        from_node_id: int,
        to_node_id: int,
        rel_type: Optional[str] = None
    ) -> int:
        """删除两个节点之间的关系"""
        if rel_type:
            query = f"""
            MATCH (a)-[r:{rel_type}]->(b)
            WHERE id(a) = $from_id AND id(b) = $to_id
            DELETE r
            RETURN count(r) as deleted_count
            """
        else:
            query = """
            MATCH (a)-[r]->(b)
            WHERE id(a) = $from_id AND id(b) = $to_id
            DELETE r
            RETURN count(r) as deleted_count
            """
        
        result = self.session.run(query, from_id=from_node_id, to_id=to_node_id)
        record = result.single()
        
        return record["deleted_count"] if record else 0
    
    def count(self, rel_type: Optional[str] = None) -> int:
        """统计关系数量"""
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"
        
        result = self.session.run(query)
        record = result.single()
        
        return record["count"] if record else 0