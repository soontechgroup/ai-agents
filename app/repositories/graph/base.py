"""
图数据库 Repository 基类
提供通用的图数据库操作方法
"""

from typing import Dict, List, Any, Optional
from neo4j import Session
import logging

logger = logging.getLogger(__name__)


class BaseGraphRepository:
    """
    图数据库 Repository 基类
    所有 Neo4j Repository 都应继承此类
    """
    
    def __init__(self, session: Session):
        """
        初始化 Repository
        
        Args:
            session: Neo4j Session 实例
        """
        self.session = session
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
        
        Returns:
            查询结果列表
        """
        try:
            result = self.session.run(query, parameters or {})
            return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            raise
    
    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        执行写入操作
        
        Args:
            query: Cypher 写入语句
            parameters: 写入参数
        
        Returns:
            是否执行成功
        """
        try:
            self.session.run(query, parameters or {})
            return True
        except Exception as e:
            logger.error(f"写入操作失败: {str(e)}")
            return False
    
    def transaction(self, transaction_function, *args, **kwargs):
        """
        在事务中执行操作
        
        Args:
            transaction_function: 事务函数
            *args, **kwargs: 传递给事务函数的参数
        
        Returns:
            事务执行结果
        """
        return self.session.execute_write(transaction_function, *args, **kwargs)