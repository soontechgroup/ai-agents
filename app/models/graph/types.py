"""
图数据模型共享类型定义
包含枚举、类型别名和常量
"""

from enum import Enum
from typing import Tuple, Union, Literal


# ==================== 通用枚举 ====================

class Gender(str, Enum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class RelationshipStatus(str, Enum):
    """关系状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class Frequency(str, Enum):
    """频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    RARELY = "rarely"
    NEVER = "never"


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CONFIRMED = "confirmed"


# ==================== 节点相关枚举 ====================

class OrganizationType(str, Enum):
    """组织类型"""
    COMPANY = "company"
    NONPROFIT = "nonprofit"
    GOVERNMENT = "government"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    STARTUP = "startup"
    CORPORATION = "corporation"
    PARTNERSHIP = "partnership"
    OTHER = "other"


class LocationType(str, Enum):
    """地点类型"""
    COUNTRY = "country"
    STATE = "state"
    CITY = "city"
    DISTRICT = "district"
    STREET = "street"
    BUILDING = "building"
    ROOM = "room"
    LANDMARK = "landmark"
    ONLINE = "online"


class EventType(str, Enum):
    """事件类型"""
    MEETING = "meeting"
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    CELEBRATION = "celebration"
    TRANSACTION = "transaction"
    MILESTONE = "milestone"
    INCIDENT = "incident"
    OTHER = "other"


class ConceptCategory(str, Enum):
    """概念分类"""
    SKILL = "skill"
    KNOWLEDGE = "knowledge"
    INTEREST = "interest"
    TECHNOLOGY = "technology"
    METHODOLOGY = "methodology"
    THEORY = "theory"
    TOPIC = "topic"
    TAG = "tag"


# ==================== 关系相关枚举 ====================

class FriendshipLevel(str, Enum):
    """友谊程度"""
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    BEST_FRIEND = "best_friend"


class FamilyRelationType(str, Enum):
    """家庭关系类型"""
    PARENT = "parent"
    CHILD = "child"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    GRANDPARENT = "grandparent"
    GRANDCHILD = "grandchild"
    UNCLE = "uncle"
    AUNT = "aunt"
    COUSIN = "cousin"
    IN_LAW = "in_law"


class HierarchyType(str, Enum):
    """层级关系"""
    PEER = "peer"
    SUPERIOR = "superior"
    SUBORDINATE = "subordinate"
    MENTOR = "mentor"
    MENTEE = "mentee"


class CollaborationLevel(str, Enum):
    """协作程度"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    INTENSIVE = "intensive"


class TransactionType(str, Enum):
    """交易类型"""
    PURCHASE = "purchase"
    SALE = "sale"
    LOAN = "loan"
    INVESTMENT = "investment"
    PAYMENT = "payment"
    TRANSFER = "transfer"
    DONATION = "donation"


class InvestmentType(str, Enum):
    """投资类型"""
    EQUITY = "equity"
    DEBT = "debt"
    CONVERTIBLE = "convertible"
    GRANT = "grant"
    CROWDFUNDING = "crowdfunding"


class DistanceUnit(str, Enum):
    """距离单位"""
    METER = "meter"
    KILOMETER = "kilometer"
    MILE = "mile"
    FOOT = "foot"


class TimeUnit(str, Enum):
    """时间单位"""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


# ==================== 类型别名 ====================

# 坐标类型 (经度, 纬度)
Coordinates = Tuple[float, float]

# 地址类型
Address = Union[str, dict]

# 货币类型
Currency = Literal["USD", "EUR", "CNY", "JPY", "GBP", "AUD", "CAD", "CHF", "HKD", "SGD"]

# 语言类型
Language = Literal["en", "zh", "es", "fr", "de", "ja", "ko", "ru", "ar", "pt"]

# 优先级类型
Priority = Literal["low", "medium", "high", "urgent", "critical"]

# 评分类型 (1-5星)
Rating = Literal[1, 2, 3, 4, 5]


# ==================== 常量定义 ====================

# 默认值
DEFAULT_STRENGTH = 0.5
DEFAULT_WEIGHT = 1.0
DEFAULT_CONFIDENCE = 0.5

# 限制值
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MAX_TAGS_COUNT = 20
MAX_RELATIONSHIP_DEPTH = 10

# 验证模式
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_PATTERN = r'^[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$'
URL_PATTERN = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)$'


# ==================== 辅助函数 ====================

def confidence_to_level(confidence: float) -> ConfidenceLevel:
    """
    将置信度数值转换为等级
    
    Args:
        confidence: 0-1之间的置信度值
    
    Returns:
        置信度等级
    """
    if confidence >= 0.95:
        return ConfidenceLevel.CONFIRMED
    elif confidence >= 0.8:
        return ConfidenceLevel.VERY_HIGH
    elif confidence >= 0.6:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.4:
        return ConfidenceLevel.MEDIUM
    elif confidence >= 0.2:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


def level_to_confidence(level: ConfidenceLevel) -> float:
    """
    将置信度等级转换为数值
    
    Args:
        level: 置信度等级
    
    Returns:
        置信度数值
    """
    mapping = {
        ConfidenceLevel.CONFIRMED: 1.0,
        ConfidenceLevel.VERY_HIGH: 0.9,
        ConfidenceLevel.HIGH: 0.7,
        ConfidenceLevel.MEDIUM: 0.5,
        ConfidenceLevel.LOW: 0.3,
        ConfidenceLevel.VERY_LOW: 0.1,
    }
    return mapping.get(level, 0.5)