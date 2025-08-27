"""
Neomodel 关系模型定义
定义带属性的关系
"""

from datetime import datetime
from neomodel import (
    StructuredRel,
    StringProperty,
    DateTimeProperty,
    BooleanProperty,
    FloatProperty,
    IntegerProperty
)


class FriendshipRel(StructuredRel):
    """朋友关系模型"""
    since = DateTimeProperty(default=lambda: datetime.now())
    mutual = BooleanProperty(default=True)
    closeness = IntegerProperty(default=5)  # 1-10的亲密度


class WorksAtRel(StructuredRel):
    """工作关系模型"""
    position = StringProperty()
    department = StringProperty()
    start_date = DateTimeProperty(default=lambda: datetime.now())
    end_date = DateTimeProperty()
    is_current = BooleanProperty(default=True)
    salary = FloatProperty()


class FamilyRel(StructuredRel):
    """家庭关系模型"""
    relationship_type = StringProperty()  # 父母、子女、兄弟姐妹、配偶等
    since = DateTimeProperty()


class KnowsRel(StructuredRel):
    """认识关系模型"""
    since = DateTimeProperty(default=lambda: datetime.now())
    context = StringProperty()  # 认识的场景
    trust_level = IntegerProperty(default=5)  # 1-10的信任度