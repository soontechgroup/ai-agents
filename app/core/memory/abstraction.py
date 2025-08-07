"""
记忆体抽象接口
定义记忆系统的核心操作接口
"""
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
from datetime import datetime


class IMemory(ABC):
    """
    记忆体抽象接口
    定义记忆系统必须实现的核心操作
    """
    
    @abstractmethod
    async def encode(self, content: Any, context: Optional[Dict] = None) -> Dict:
        """
        编码：将原始内容转换为记忆表示
        
        Args:
            content: 原始内容（文本、对话、图像等）
            context: 上下文信息（用户ID、会话ID等）
            
        Returns:
            编码后的记忆字典
        """
        pass
    
    @abstractmethod
    async def store(self, memory: Dict) -> str:
        """
        存储：持久化记忆到存储系统
        
        Args:
            memory: 记忆字典
            
        Returns:
            记忆ID
        """
        pass
    
    @abstractmethod
    async def retrieve(self, query: Any, limit: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        检索：基于查询获取相关记忆
        
        Args:
            query: 查询条件（文本、向量、条件等）
            limit: 返回结果数量限制
            filters: 额外的过滤条件
            
        Returns:
            相关记忆列表
        """
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: Dict) -> bool:
        """
        更新：修改已存在的记忆
        
        Args:
            memory_id: 记忆ID
            updates: 更新内容
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    async def consolidate(self, memory_id: str, factor: float = 1.2) -> bool:
        """
        巩固：增强记忆强度
        
        Args:
            memory_id: 记忆ID
            factor: 强化因子
            
        Returns:
            是否巩固成功
        """
        pass
    
    @abstractmethod
    async def decay(self, memory_id: str, rate: float = 0.1) -> bool:
        """
        衰减：减弱记忆强度（遗忘曲线）
        
        Args:
            memory_id: 记忆ID
            rate: 衰减率
            
        Returns:
            是否衰减成功
        """
        pass
    
    @abstractmethod
    async def forget(self, memory_id: str) -> bool:
        """
        遗忘：删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    async def associate(self, memory_id1: str, memory_id2: str, relation_type: str, strength: float = 0.5) -> bool:
        """
        关联：建立记忆之间的联系
        
        Args:
            memory_id1: 第一个记忆ID
            memory_id2: 第二个记忆ID
            relation_type: 关系类型（如：similar, causal, temporal）
            strength: 关联强度
            
        Returns:
            是否关联成功
        """
        pass
    
    @abstractmethod
    async def get_associations(self, memory_id: str, relation_type: Optional[str] = None) -> List[Dict]:
        """
        获取关联：获取与指定记忆相关的其他记忆
        
        Args:
            memory_id: 记忆ID
            relation_type: 关系类型过滤
            
        Returns:
            关联记忆列表
        """
        pass