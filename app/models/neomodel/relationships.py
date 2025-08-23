"""
Neomodel 关系模型定义
定义所有关系类型的常量和属性
"""

from datetime import datetime
from neomodel import (
    StructuredRel,
    StringProperty,
    DateTimeProperty,
    FloatProperty,
    IntegerProperty,
    BooleanProperty,
    ArrayProperty
)


class BaseRelationship(StructuredRel):
    """关系基类"""
    created_at = DateTimeProperty(default_factory=datetime.now)
    updated_at = DateTimeProperty(default_factory=datetime.now)
    confidence = FloatProperty(default=1.0)
    data_source = StringProperty()  # 重命名为 data_source 避免冲突


# 社交关系
class FRIEND_OF(BaseRelationship):
    """朋友关系"""
    since = DateTimeProperty()
    closeness = FloatProperty(default=0.5)  # 0-1
    mutual = BooleanProperty(default=True)


class FAMILY_OF(BaseRelationship):
    """家庭关系"""
    relationship_type = StringProperty(choices={
        'parent': 'Parent',
        'child': 'Child',
        'sibling': 'Sibling',
        'spouse': 'Spouse',
        'cousin': 'Cousin',
        'grandparent': 'Grandparent',
        'grandchild': 'Grandchild',
        'other': 'Other'
    })


class KNOWS(BaseRelationship):
    """认识关系"""
    context = StringProperty()
    since = DateTimeProperty()


# 专业关系
class WORKS_AT(BaseRelationship):
    """工作关系"""
    position = StringProperty()
    department = StringProperty()
    start_date = DateTimeProperty()
    end_date = DateTimeProperty()
    is_current = BooleanProperty(default=True)
    salary = FloatProperty()


class COLLEAGUE_OF(BaseRelationship):
    """同事关系"""
    department = StringProperty()
    projects = ArrayProperty(StringProperty())


class REPORTS_TO(BaseRelationship):
    """汇报关系"""
    direct = BooleanProperty(default=True)
    department = StringProperty()


class MANAGES(BaseRelationship):
    """管理关系"""
    department = StringProperty()
    team_size = IntegerProperty()


class MEMBER_OF(BaseRelationship):
    """成员关系"""
    role = StringProperty()
    since = DateTimeProperty()
    is_active = BooleanProperty(default=True)


# 地理关系
class LOCATED_IN(BaseRelationship):
    """位于关系"""
    address = StringProperty()
    is_primary = BooleanProperty(default=False)
    since = DateTimeProperty()


# 事件关系
class ATTENDED(BaseRelationship):
    """参加关系"""
    role = StringProperty(choices={
        'attendee': 'Attendee',
        'speaker': 'Speaker',
        'organizer': 'Organizer',
        'sponsor': 'Sponsor',
        'volunteer': 'Volunteer'
    })
    registration_date = DateTimeProperty()
    attended = BooleanProperty(default=True)


class PARTICIPATED_IN(BaseRelationship):
    """参与关系"""
    role = StringProperty()
    contribution = StringProperty()
    hours = IntegerProperty()


class ORGANIZED(BaseRelationship):
    """组织关系"""
    role = StringProperty()
    responsibilities = ArrayProperty(StringProperty())


# 项目关系
class COLLABORATES_ON(BaseRelationship):
    """协作关系"""
    role = StringProperty()
    contribution_percentage = FloatProperty()
    tasks = ArrayProperty(StringProperty())


# 所有权关系
class OWNS(BaseRelationship):
    """拥有关系"""
    acquired_date = DateTimeProperty()
    quantity = IntegerProperty(default=1)
    value = FloatProperty()


class USES(BaseRelationship):
    """使用关系"""
    frequency = StringProperty(choices={
        'daily': 'Daily',
        'weekly': 'Weekly',
        'monthly': 'Monthly',
        'occasionally': 'Occasionally'
    })
    purpose = StringProperty()
    satisfaction = FloatProperty()  # 0-1


# 分类关系
class TAGGED_WITH(BaseRelationship):
    """标签关系"""
    relevance = FloatProperty(default=1.0)
    auto_generated = BooleanProperty(default=False)


class CATEGORIZED_AS(BaseRelationship):
    """分类关系"""
    primary = BooleanProperty(default=False)
    rank = IntegerProperty()