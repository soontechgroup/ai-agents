"""
记忆体类型定义
定义记忆系统中使用的枚举和类型
"""
from enum import Enum
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class MemoryType(str, Enum):
    """记忆类型枚举"""
    
    # 基于时间维度
    WORKING = "working"          # 工作记忆（当前任务上下文）
    SHORT_TERM = "short_term"    # 短期记忆（最近的交互）
    LONG_TERM = "long_term"      # 长期记忆（持久化知识）
    
    # 基于内容类型
    EPISODIC = "episodic"        # 情景记忆（具体事件和经历）
    SEMANTIC = "semantic"        # 语义记忆（事实和概念知识）
    PROCEDURAL = "procedural"    # 程序记忆（技能和行为模式）
    
    # 特殊类型
    EMOTIONAL = "emotional"      # 情感记忆（情绪和感受）
    SENSORY = "sensory"         # 感官记忆（视觉、听觉等）


class MemoryStrength(float, Enum):
    """记忆强度枚举"""
    WEAK = 0.2         # 弱记忆（容易遗忘）
    MEDIUM = 0.5       # 中等记忆
    STRONG = 0.8       # 强记忆（不易遗忘）
    PERMANENT = 1.0    # 永久记忆（核心知识）


class MemoryImportance(float, Enum):
    """记忆重要性枚举"""
    TRIVIAL = 0.1      # 琐碎的
    LOW = 0.3          # 低重要性
    NORMAL = 0.5       # 一般重要性
    HIGH = 0.7         # 高重要性
    CRITICAL = 0.9     # 关键重要性


class RelationType(str, Enum):
    """记忆关联类型"""
    SIMILAR = "similar"           # 相似关系
    CAUSAL = "causal"            # 因果关系
    TEMPORAL = "temporal"        # 时间关系
    HIERARCHICAL = "hierarchical"  # 层次关系
    CONTRADICTORY = "contradictory"  # 矛盾关系
    COMPLEMENTARY = "complementary"  # 互补关系


class MemorySource(str, Enum):
    """记忆来源"""
    CONVERSATION = "conversation"  # 对话产生
    MANUAL = "manual"             # 手动输入
    LEARNED = "learned"           # 学习获得
    INFERRED = "inferred"         # 推理得出
    EXTERNAL = "external"         # 外部导入


class MemoryMetadata(TypedDict, total=False):
    """记忆元数据类型"""
    user_id: str                 # 用户ID
    session_id: str              # 会话ID
    conversation_id: str         # 对话ID
    digital_human_id: str        # 数字人ID
    timestamp: datetime          # 时间戳
    location: Optional[str]      # 地点信息
    emotion: Optional[str]       # 情感状态
    confidence: float            # 置信度
    tags: List[str]             # 标签
    source: MemorySource        # 来源
    context: Dict[str, Any]     # 其他上下文


class MemoryEntity(TypedDict):
    """记忆中的实体"""
    type: str                    # 实体类型（人物、地点、事件等）
    value: str                   # 实体值
    role: Optional[str]          # 实体角色
    attributes: Dict[str, Any]   # 实体属性


class MemoryDocument(TypedDict):
    """完整的记忆文档结构"""
    memory_id: str               # 唯一标识
    memory_type: MemoryType      # 记忆类型
    content: str                 # 记忆内容
    summary: Optional[str]       # 简短摘要
    keywords: List[str]          # 关键词
    entities: List[MemoryEntity] # 实体列表
    
    # 向量和智能特征
    embedding: Optional[List[float]]  # 向量嵌入
    
    # 记忆动态属性
    strength: float              # 记忆强度
    importance: float            # 重要性
    access_count: int            # 访问次数
    last_accessed: datetime      # 最后访问时间
    decay_rate: float           # 衰减率
    
    # 元数据
    metadata: MemoryMetadata     # 元数据
    created_at: datetime         # 创建时间
    updated_at: datetime         # 更新时间
    
    # 关联信息
    associations: List[Dict[str, Any]]  # 关联的其他记忆