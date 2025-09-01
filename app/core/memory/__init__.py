"""
记忆体抽象层
提供AI记忆系统的核心抽象和接口定义
"""

from .abstraction import IMemory
from .types import MemoryType, MemoryStrength

__all__ = [
    "IMemory",
    "MemoryType", 
    "MemoryStrength"
]