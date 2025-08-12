"""
Neo4j 数据库连接和基础操作工具类
提供简单的节点创建、关系创建和搜索功能
"""

from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver
from contextlib import contextmanager
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Neo4j 数据库连接管理器（单例模式）"""
    
    _instance = None
    _driver: Optional[Driver] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化连接"""
        if not self._driver:
            self._connect()
    
    def _connect(self):
        """创建数据库连接"""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            # 验证连接
            self._driver.verify_connectivity()
            logger.info(f"✅ Neo4j 连接成功: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {str(e)}")
            raise
    
    def get_driver(self) -> Driver:
        """获取驱动实例"""
        if not self._driver:
            self._connect()
        return self._driver
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j 连接已关闭")
    
    @contextmanager
    def session(self):
        """获取会话上下文管理器"""
        driver = self.get_driver()
        session = driver.session(database=settings.NEO4J_DATABASE)
        try:
            yield session
        finally:
            session.close()


class Neo4jUtil:
    """Neo4j 基础操作工具类"""
    
    def __init__(self):
        self.connection = Neo4jConnection()
    
    # ==================== 基础写入操作 ====================
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建节点
        
        Args:
            label: 节点标签（如 'User', 'DigitalHuman'）
            properties: 节点属性字典
        
        Returns:
            创建的节点信息
        
        Example:
            >>> neo4j_util.create_node('User', {'name': '张三', 'age': 25})
        """
        with self.connection.session() as session:
            query = f"""
            CREATE (n:{label} $props)
            RETURN n, id(n) as node_id
            """
            result = session.run(query, props=properties)
            record = result.single()
            
            if record:
                return {
                    "id": record["node_id"],
                    "label": label,
                    "properties": dict(record["n"])
                }
    
    def create_relationship(
        self,
        from_node_id: int,
        to_node_id: int,
        rel_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """
        创建两个节点之间的关系
        
        Args:
            from_node_id: 起始节点ID
            to_node_id: 目标节点ID
            rel_type: 关系类型（如 'OWNS', 'FOLLOWS'）
            properties: 关系属性（可选）
        
        Returns:
            是否创建成功
        
        Example:
            >>> neo4j_util.create_relationship(1, 2, 'OWNS', {'since': '2024-01-01'})
        """
        with self.connection.session() as session:
            props = properties or {}
            query = f"""
            MATCH (a), (b)
            WHERE id(a) = $from_id AND id(b) = $to_id
            CREATE (a)-[r:{rel_type} $props]->(b)
            RETURN r
            """
            result = session.run(query, from_id=from_node_id, to_id=to_node_id, props=props)
            return result.single() is not None
    
    # ==================== 基础搜索操作 ====================
    
    def find_node_by_property(self, label: str, property_name: str, property_value: Any) -> Optional[Dict[str, Any]]:
        """
        根据属性查找单个节点
        
        Args:
            label: 节点标签
            property_name: 属性名
            property_value: 属性值
        
        Returns:
            节点信息或 None
        
        Example:
            >>> neo4j_util.find_node_by_property('User', 'name', '张三')
        """
        with self.connection.session() as session:
            query = f"""
            MATCH (n:{label})
            WHERE n.{property_name} = $value
            RETURN n, id(n) as node_id
            LIMIT 1
            """
            result = session.run(query, value=property_value)
            record = result.single()
            
            if record:
                return {
                    "id": record["node_id"],
                    "label": label,
                    "properties": dict(record["n"])
                }
            return None
    
    def find_all_nodes(self, label: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        查找某个标签的所有节点
        
        Args:
            label: 节点标签
            limit: 返回数量限制
        
        Returns:
            节点列表
        
        Example:
            >>> neo4j_util.find_all_nodes('User', limit=10)
        """
        with self.connection.session() as session:
            query = f"""
            MATCH (n:{label})
            RETURN n, id(n) as node_id
            LIMIT {limit}
            """
            result = session.run(query)
            
            nodes = []
            for record in result:
                nodes.append({
                    "id": record["node_id"],
                    "label": label,
                    "properties": dict(record["n"])
                })
            return nodes
    
    def find_connected_nodes(self, node_id: int, rel_type: str = None, direction: str = "both") -> List[Dict[str, Any]]:
        """
        查找与某个节点相连的所有节点
        
        Args:
            node_id: 节点ID
            rel_type: 关系类型（可选，不指定则查找所有类型）
            direction: 方向（'outgoing'-出边, 'incoming'-入边, 'both'-双向）
        
        Returns:
            相连节点列表
        
        Example:
            >>> neo4j_util.find_connected_nodes(1, 'OWNS', 'outgoing')
        """
        with self.connection.session() as session:
            rel_pattern = f":{rel_type}" if rel_type else ""
            
            if direction == "outgoing":
                pattern = f"(a)-[{rel_pattern}]->(b)"
            elif direction == "incoming":
                pattern = f"(a)<-[{rel_pattern}]-(b)"
            else:  # both
                pattern = f"(a)-[{rel_pattern}]-(b)"
            
            query = f"""
            MATCH {pattern}
            WHERE id(a) = $node_id
            RETURN b, id(b) as node_id, labels(b) as labels
            """
            result = session.run(query, node_id=node_id)
            
            nodes = []
            for record in result:
                nodes.append({
                    "id": record["node_id"],
                    "labels": record["labels"],
                    "properties": dict(record["b"])
                })
            return nodes
    
    def search_nodes_by_keyword(self, label: str, keyword: str, properties: List[str]) -> List[Dict[str, Any]]:
        """
        在指定属性中搜索包含关键词的节点
        
        Args:
            label: 节点标签
            keyword: 搜索关键词
            properties: 要搜索的属性列表
        
        Returns:
            匹配的节点列表
        
        Example:
            >>> neo4j_util.search_nodes_by_keyword('User', '张', ['name', 'description'])
        """
        with self.connection.session() as session:
            # 构建 WHERE 条件
            conditions = [f"n.{prop} CONTAINS $keyword" for prop in properties]
            where_clause = " OR ".join(conditions)
            
            query = f"""
            MATCH (n:{label})
            WHERE {where_clause}
            RETURN n, id(n) as node_id
            """
            result = session.run(query, keyword=keyword)
            
            nodes = []
            for record in result:
                nodes.append({
                    "id": record["node_id"],
                    "label": label,
                    "properties": dict(record["n"])
                })
            return nodes
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行自定义 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
        
        Returns:
            查询结果列表
        
        Example:
            >>> query = "MATCH (u:User)-[:OWNS]->(d:DigitalHuman) RETURN u.name, d.name"
            >>> neo4j_util.execute_query(query)
        """
        with self.connection.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def close(self):
        """关闭连接"""
        self.connection.close()


# 创建全局实例
neo4j_util = Neo4jUtil()