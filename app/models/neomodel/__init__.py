"""
Neomodel ORM 模型
提供与Neo4j数据库的ORM映射
"""

from app.models.neomodel.base import BaseNode
from app.models.neomodel.nodes import (
    Person,
    Organization,
    Location,
    Event,
    Project,
    Product,
    Tag,
    Category
)
from app.models.neomodel.relationships import (
    FRIEND_OF,
    FAMILY_OF,
    KNOWS,
    WORKS_AT,
    COLLEAGUE_OF,
    REPORTS_TO,
    MANAGES,
    MEMBER_OF,
    LOCATED_IN,
    ATTENDED,
    PARTICIPATED_IN,
    ORGANIZED,
    COLLABORATES_ON,
    OWNS,
    USES,
    TAGGED_WITH,
    CATEGORIZED_AS
)

__all__ = [
    # Base
    'BaseNode',
    
    # Nodes
    'Person',
    'Organization',
    'Location',
    'Event',
    'Project',
    'Product',
    'Tag',
    'Category',
    
    # Relationships
    'FRIEND_OF',
    'FAMILY_OF',
    'KNOWS',
    'WORKS_AT',
    'COLLEAGUE_OF',
    'REPORTS_TO',
    'MANAGES',
    'MEMBER_OF',
    'LOCATED_IN',
    'ATTENDED',
    'PARTICIPATED_IN',
    'ORGANIZED',
    'COLLABORATES_ON',
    'OWNS',
    'USES',
    'TAGGED_WITH',
    'CATEGORIZED_AS'
]