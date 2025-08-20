"""
Neo4j 图数据库依赖注入
提供 Repository 模式所需的依赖
"""

from app.core.neo4j import neo4j_db
from app.repositories.graph import GraphRepository


def get_neo4j_session():
    """
    获取 Neo4j Session 依赖
    用于 FastAPI 的 Depends 注入（底层操作）
    
    Example:
        from fastapi import Depends
        from app.dependencies.graph import get_neo4j_session
        
        @router.get("/nodes")
        async def get_nodes(session = Depends(get_neo4j_session)):
            node_repo = GraphNodeRepository(session)
            return node_repo.find_all()
    """
    with neo4j_db.session() as session:
        yield session


def get_graph_repository():
    """
    获取统一的 GraphRepository 依赖（推荐使用）
    提供更简洁的图数据库操作接口
    
    Example:
        from fastapi import Depends
        from app.dependencies.graph import get_graph_repository
        
        @router.get("/nodes")
        async def get_nodes(graph = Depends(get_graph_repository)):
            # 直接使用统一接口
            return graph.nodes.find_all()
        
        @router.post("/users")
        async def create_user(
            user_data: dict,
            graph = Depends(get_graph_repository)
        ):
            # 使用组合操作
            return graph.create_node_with_relationships(
                "User", 
                user_data,
                connections=[...]
            )
    """
    with neo4j_db.session() as session:
        yield GraphRepository(session)