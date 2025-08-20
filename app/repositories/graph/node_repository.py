"""图节点操作 Repository"""

from typing import Dict, List, Any, Optional
from .base import BaseGraphRepository
import logging

logger = logging.getLogger(__name__)


class GraphNodeRepository(BaseGraphRepository):
    """节点操作 Repository"""
    
    def create(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """创建节点"""
        query = f"""
        CREATE (n:{label} $props)
        RETURN n, id(n) as node_id
        """
        
        result = self.session.run(query, props=properties)
        record = result.single()
        
        if record:
            return {
                "id": record["node_id"],
                "label": label,
                "properties": dict(record["n"])
            }
        return None
    
    def find_by_id(self, node_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 查找节点"""
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        RETURN n, id(n) as node_id, labels(n) as labels
        """
        
        result = self.session.run(query, node_id=node_id)
        record = result.single()
        
        if record:
            return {
                "id": record["node_id"],
                "labels": record["labels"],
                "properties": dict(record["n"])
            }
        return None
    
    def find_by_property(self, label: str, property_name: str, property_value: Any) -> Optional[Dict[str, Any]]:
        """根据属性查找单个节点"""
        query = f"""
        MATCH (n:{label})
        WHERE n.{property_name} = $value
        RETURN n, id(n) as node_id
        LIMIT 1
        """
        
        result = self.session.run(query, value=property_value)
        record = result.single()
        
        if record:
            return {
                "id": record["node_id"],
                "label": label,
                "properties": dict(record["n"])
            }
        return None
    
    def find_all(self, label: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """查找所有节点"""
        if label:
            query = f"""
            MATCH (n:{label})
            RETURN n, id(n) as node_id
            LIMIT $limit
            """
        else:
            query = """
            MATCH (n)
            RETURN n, id(n) as node_id, labels(n) as labels
            LIMIT $limit
            """
        
        result = self.session.run(query, limit=limit)
        
        nodes = []
        for record in result:
            node_data = {
                "id": record["node_id"],
                "properties": dict(record["n"])
            }
            if label:
                node_data["label"] = label
            else:
                node_data["labels"] = record["labels"]
            nodes.append(node_data)
        
        return nodes
    
    def search(self, label: str, keyword: str, properties: List[str]) -> List[Dict[str, Any]]:
        """在指定属性中搜索包含关键词的节点"""
        # 构建 WHERE 条件
        conditions = [f"n.{prop} CONTAINS $keyword" for prop in properties]
        where_clause = " OR ".join(conditions)
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_clause}
        RETURN n, id(n) as node_id
        """
        
        result = self.session.run(query, keyword=keyword)
        
        nodes = []
        for record in result:
            nodes.append({
                "id": record["node_id"],
                "label": label,
                "properties": dict(record["n"])
            })
        
        return nodes
    
    def update(self, node_id: int, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新节点属性"""
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        SET n += $props
        RETURN n, id(n) as node_id, labels(n) as labels
        """
        
        result = self.session.run(query, node_id=node_id, props=properties)
        record = result.single()
        
        if record:
            return {
                "id": record["node_id"],
                "labels": record["labels"],
                "properties": dict(record["n"])
            }
        return None
    
    def delete(self, node_id: int) -> bool:
        """删除节点"""
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """
        
        result = self.session.run(query, node_id=node_id)
        record = result.single()
        
        return record["deleted_count"] > 0 if record else False
    
    def exists(self, node_id: int) -> bool:
        """检查节点是否存在"""
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        RETURN count(n) > 0 as exists
        """
        
        result = self.session.run(query, node_id=node_id)
        record = result.single()
        
        return record["exists"] if record else False
    
    def count(self, label: Optional[str] = None) -> int:
        """统计节点数量"""
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"
        
        result = self.session.run(query)
        record = result.single()
        
        return record["count"] if record else 0