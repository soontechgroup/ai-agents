"""
图数据库通用查询仓储
处理跨节点类型的图查询操作
"""

from typing import Dict, List, Any, Optional
import logging
from neomodel import db

logger = logging.getLogger(__name__)


class GraphRepository:
    """
    图数据库通用查询仓储
    提供跨节点类型的查询操作
    """
    
    def list_all_relationships(
        self, 
        relationship_type: Optional[str] = None, 
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        获取图数据库中的所有关系
        
        Args:
            relationship_type: 可选的关系类型过滤
            limit: 返回数量限制
            
        Returns:
            包含关系列表和总数的字典
        """
        try:
            # 构建查询
            if relationship_type:
                query = f"""
                    MATCH (a)-[r:{relationship_type}]->(b)
                    RETURN id(a) as from_id, a.uid as from_uid, a.name as from_name,
                           id(b) as to_id, b.uid as to_uid, b.name as to_name,
                           type(r) as type, properties(r) as properties
                    LIMIT {limit}
                """
            else:
                query = f"""
                    MATCH (a)-[r]->(b)
                    WHERE labels(a)[0] = 'Person' OR labels(a)[0] = 'Organization'
                    RETURN id(a) as from_id, a.uid as from_uid, a.name as from_name,
                           id(b) as to_id, b.uid as to_uid, b.name as to_name,
                           type(r) as type, properties(r) as properties
                    LIMIT {limit}
                """
            
            results, _ = db.cypher_query(query)
            
            relationships = []
            for row in results:
                relationships.append({
                    "from": row[1] or str(row[0]),  # 使用uid或id
                    "from_name": row[2],
                    "to": row[4] or str(row[3]),    # 使用uid或id
                    "to_name": row[5],
                    "type": row[6],
                    "properties": row[7] if row[7] else {}
                })
            
            logger.info(f"获取到 {len(relationships)} 个关系")
            
            return {
                "relationships": relationships,
                "total": len(relationships)
            }
            
        except Exception as e:
            logger.error(f"获取关系列表失败: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            包含节点和关系统计的字典
        """
        try:
            # 统计各类节点数量
            stats_query = """
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """
            results, _ = db.cypher_query(stats_query)
            
            node_stats = {}
            for row in results:
                if row[0]:  # 确保label不为空
                    node_stats[row[0]] = row[1]
            
            # 统计关系数量
            rel_query = """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """
            rel_results, _ = db.cypher_query(rel_query)
            
            rel_stats = {}
            for row in rel_results:
                if row[0]:
                    rel_stats[row[0]] = row[1]
            
            return {
                "nodes": node_stats,
                "relationships": rel_stats,
                "total_nodes": sum(node_stats.values()),
                "total_relationships": sum(rel_stats.values())
            }
        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            return {
                "error": str(e),
                "nodes": {},
                "relationships": {},
                "total_nodes": 0,
                "total_relationships": 0
            }
    
    def find_shortest_path(self, from_uid: str, to_uid: str) -> Optional[Dict[str, Any]]:
        """
        查找两个节点之间的最短路径
        
        Args:
            from_uid: 起始节点UID
            to_uid: 目标节点UID
            
        Returns:
            包含路径信息的字典或None
        """
        try:
            query = """
                MATCH path = shortestPath(
                    (from:Person {uid: $from_uid})-[*]-(to:Person {uid: $to_uid})
                )
                RETURN [n in nodes(path) | {uid: n.uid, name: n.name}] as nodes,
                       [r in relationships(path) | type(r)] as relationships
            """
            
            results, _ = db.cypher_query(
                query,
                {"from_uid": from_uid, "to_uid": to_uid}
            )
            
            if results:
                return {
                    "nodes": results[0][0],
                    "relationships": results[0][1],
                    "length": len(results[0][1])
                }
            return None
        except Exception as e:
            logger.error(f"查找最短路径失败: {str(e)}")
            return None
    
    def execute_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> tuple:
        """
        执行原生Cypher查询
        
        Args:
            query: Cypher查询语句
            params: 查询参数
        
        Returns:
            查询结果和元数据的元组
        """
        try:
            return db.cypher_query(query, params or {})
        except Exception as e:
            logger.error(f"执行Cypher查询失败: {str(e)}")
            raise