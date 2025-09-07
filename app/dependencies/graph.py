"""
Neo4j 图数据库依赖注入
提供基于Neomodel的服务依赖
"""

from app.services.graph_service import GraphService


def get_graph_service() -> GraphService:
    """
    获取图数据库服务实例
    
    Returns:
        GraphService实例
    """
    return GraphService()