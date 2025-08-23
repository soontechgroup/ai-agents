"""
Neo4j 图数据库依赖注入
提供基于Neomodel的服务依赖
"""

from app.services.graph_service import GraphService
from app.repositories.neomodel import (
    PersonRepository,
    OrganizationRepository,
    LocationRepository,
    EventRepository,
    ProjectRepository,
    ProductRepository,
    TagRepository,
    CategoryRepository
)


def get_graph_service() -> GraphService:
    """
    获取图数据库服务实例
    
    Returns:
        GraphService实例
    """
    return GraphService()


def get_person_repository() -> PersonRepository:
    """获取人员仓储"""
    return PersonRepository()


def get_organization_repository() -> OrganizationRepository:
    """获取组织仓储"""
    return OrganizationRepository()


def get_location_repository() -> LocationRepository:
    """获取地点仓储"""
    return LocationRepository()


def get_event_repository() -> EventRepository:
    """获取事件仓储"""
    return EventRepository()


def get_project_repository() -> ProjectRepository:
    """获取项目仓储"""
    return ProjectRepository()


def get_product_repository() -> ProductRepository:
    """获取产品仓储"""
    return ProductRepository()


def get_tag_repository() -> TagRepository:
    """获取标签仓储"""
    return TagRepository()


def get_category_repository() -> CategoryRepository:
    """获取分类仓储"""
    return CategoryRepository()