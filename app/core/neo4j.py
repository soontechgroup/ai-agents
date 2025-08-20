"""
Neo4j 数据库连接管理
"""

from typing import Optional
from neo4j import GraphDatabase, Driver
from contextlib import contextmanager
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jDatabase:
    """Neo4j 数据库连接管理器"""
    
    _instance: Optional['Neo4jDatabase'] = None
    _driver: Optional[Driver] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._driver:
            self._initialize_driver()
    
    def _initialize_driver(self):
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            # 验证连接
            self._driver.verify_connectivity()
            logger.info(f"✅ Neo4j 连接成功: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {str(e)}")
            raise
    
    @property
    def driver(self) -> Driver:
        if not self._driver:
            self._initialize_driver()
        return self._driver
    
    @contextmanager
    def session(self):
        """获取会话上下文管理器"""
        session = self.driver.session(database=settings.NEO4J_DATABASE)
        try:
            yield session
        finally:
            session.close()
    
    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j 连接已关闭")


neo4j_db = Neo4jDatabase()


def get_neo4j_session():
    """获取 Neo4j Session（用于依赖注入）"""
    with neo4j_db.session() as session:
        yield session