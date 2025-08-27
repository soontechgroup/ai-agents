"""
Neomodel 节点模型定义
"""

from datetime import date
from neomodel import (
    StringProperty,
    IntegerProperty,
    FloatProperty,
    BooleanProperty,
    DateProperty,
    ArrayProperty,
    JSONProperty,
    EmailProperty,
    RelationshipTo,
    RelationshipFrom,
    Relationship
)

from app.models.neomodel.base import BaseNode
from app.models.neomodel.relationships import (
    FriendshipRel, WorksAtRel, FamilyRel, KnowsRel
)


class Person(BaseNode):
    """人员节点"""
    
    # 基本信息
    name = StringProperty(required=True, index=True)
    email = EmailProperty(unique_index=True)
    phone = StringProperty()
    
    # 详细信息
    age = IntegerProperty()
    gender = StringProperty(choices={'male': 'Male', 'female': 'Female', 'other': 'Other'})
    birth_date = DateProperty()
    nationality = StringProperty()
    
    # 职业信息
    occupation = StringProperty()
    education = StringProperty()
    skills = ArrayProperty(StringProperty())
    
    # 社交信息
    bio = StringProperty()
    interests = ArrayProperty(StringProperty())
    social_links = JSONProperty()
    
    # 关系定义（使用关系模型）
    friends = Relationship('Person', 'FRIEND_OF', model=FriendshipRel)
    family = Relationship('Person', 'FAMILY_OF', model=FamilyRel)
    knows = RelationshipTo('Person', 'KNOWS', model=KnowsRel)
    works_at = RelationshipTo('Organization', 'WORKS_AT', model=WorksAtRel)
    located_in = RelationshipTo('Location', 'LOCATED_IN')
    attended = RelationshipTo('Event', 'ATTENDED')
    participates_in = RelationshipTo('Project', 'PARTICIPATES_IN')
    owns = RelationshipTo('Product', 'OWNS')
    
    class Meta:
        app_label = 'graph'


class Organization(BaseNode):
    """组织节点"""
    
    # 基本信息
    name = StringProperty(required=True, unique_index=True)
    org_type = StringProperty(choices={
        'company': 'Company',
        'nonprofit': 'Non-profit',
        'government': 'Government',
        'educational': 'Educational',
        'other': 'Other'
    })
    
    # 详细信息
    description = StringProperty()
    founded_date = DateProperty()
    industry = StringProperty()
    size = StringProperty()
    revenue = FloatProperty()
    
    # 联系信息
    website = StringProperty()
    email = EmailProperty()
    phone = StringProperty()
    headquarters = StringProperty()
    
    # 关系定义
    employees = RelationshipFrom('Person', 'WORKS_AT')
    located_in = RelationshipTo('Location', 'LOCATED_IN')
    subsidiaries = RelationshipTo('Organization', 'SUBSIDIARY_OF')
    parent_org = RelationshipFrom('Organization', 'SUBSIDIARY_OF')
    partners = Relationship('Organization', 'PARTNERS_WITH')
    organizes = RelationshipTo('Event', 'ORGANIZES')
    owns = RelationshipTo('Product', 'OWNS')
    
    class Meta:
        app_label = 'graph'


class Location(BaseNode):
    """地点节点"""
    
    # 基本信息
    name = StringProperty(required=True, index=True)
    location_type = StringProperty(choices={
        'country': 'Country',
        'state': 'State',
        'city': 'City',
        'district': 'District',
        'building': 'Building',
        'other': 'Other'
    })
    
    # 地理信息
    latitude = FloatProperty()
    longitude = FloatProperty()
    address = StringProperty()
    postal_code = StringProperty()
    
    # 附加信息
    population = IntegerProperty()
    area = FloatProperty()
    timezone = StringProperty()
    description = StringProperty()
    
    # 关系定义
    residents = RelationshipFrom('Person', 'LOCATED_IN')
    organizations = RelationshipFrom('Organization', 'LOCATED_IN')
    events = RelationshipFrom('Event', 'LOCATED_IN')
    contains = RelationshipTo('Location', 'CONTAINS')
    part_of = RelationshipFrom('Location', 'CONTAINS')
    
    class Meta:
        app_label = 'graph'


class Event(BaseNode):
    """事件节点"""
    
    # 基本信息
    name = StringProperty(required=True, index=True)
    event_type = StringProperty()
    description = StringProperty()
    
    # 时间信息
    start_date = DateProperty()
    end_date = DateProperty()
    duration = IntegerProperty()  # 分钟
    
    # 附加信息
    capacity = IntegerProperty()
    ticket_price = FloatProperty()
    tags = ArrayProperty(StringProperty())
    
    # 关系定义
    attendees = RelationshipFrom('Person', 'ATTENDED')
    organizers = RelationshipFrom('Organization', 'ORGANIZES')
    located_in = RelationshipTo('Location', 'LOCATED_IN')
    
    class Meta:
        app_label = 'graph'


class Project(BaseNode):
    """项目节点"""
    
    # 基本信息
    name = StringProperty(required=True, unique_index=True)
    description = StringProperty()
    status = StringProperty(choices={
        'planning': 'Planning',
        'active': 'Active',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    })
    
    # 时间信息
    start_date = DateProperty()
    end_date = DateProperty()
    deadline = DateProperty()
    
    # 项目信息
    budget = FloatProperty()
    progress = IntegerProperty()  # 0-100
    priority = StringProperty(choices={
        'low': 'Low',
        'medium': 'Medium',
        'high': 'High',
        'critical': 'Critical'
    })
    tags = ArrayProperty(StringProperty())
    
    # 关系定义
    participants = RelationshipFrom('Person', 'PARTICIPATES_IN')
    organizations = RelationshipFrom('Organization', 'SPONSORS')
    dependencies = RelationshipTo('Project', 'DEPENDS_ON')
    
    class Meta:
        app_label = 'graph'


class Product(BaseNode):
    """产品节点"""
    
    # 基本信息
    name = StringProperty(required=True, index=True)
    sku = StringProperty(unique_index=True)
    description = StringProperty()
    category = StringProperty()
    
    # 产品信息
    price = FloatProperty()
    cost = FloatProperty()
    stock = IntegerProperty()
    weight = FloatProperty()
    dimensions = JSONProperty()
    
    # 附加信息
    brand = StringProperty()
    manufacturer = StringProperty()
    release_date = DateProperty()
    tags = ArrayProperty(StringProperty())
    features = ArrayProperty(StringProperty())
    
    # 关系定义
    owned_by = RelationshipFrom('Person', 'OWNS')
    organization_owns = RelationshipFrom('Organization', 'OWNS')
    related_products = Relationship('Product', 'RELATED_TO')
    
    class Meta:
        app_label = 'graph'


class Tag(BaseNode):
    """标签节点"""
    
    name = StringProperty(required=True, unique_index=True)
    category = StringProperty()
    description = StringProperty()
    color = StringProperty()
    
    # 关系定义
    tagged_persons = RelationshipFrom('Person', 'TAGGED_WITH')
    tagged_organizations = RelationshipFrom('Organization', 'TAGGED_WITH')
    tagged_events = RelationshipFrom('Event', 'TAGGED_WITH')
    tagged_projects = RelationshipFrom('Project', 'TAGGED_WITH')
    tagged_products = RelationshipFrom('Product', 'TAGGED_WITH')
    
    class Meta:
        app_label = 'graph'


class Category(BaseNode):
    """分类节点"""
    
    name = StringProperty(required=True, unique_index=True)
    description = StringProperty()
    level = IntegerProperty(default=0)
    order = IntegerProperty(default=0)
    
    # 关系定义
    parent = RelationshipFrom('Category', 'SUBCATEGORY_OF')
    children = RelationshipTo('Category', 'SUBCATEGORY_OF')
    items = RelationshipFrom('BaseNode', 'CATEGORIZED_AS')
    
    class Meta:
        app_label = 'graph'