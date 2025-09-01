"""
Neomodel ORM 配置
提供Neomodel与Neo4j数据库的连接配置
"""

import logging
from neomodel import config as neomodel_config, db
from app.core.config import settings

logger = logging.getLogger(__name__)


def init_neomodel():
    """
    初始化Neomodel连接
    """
    try:
        # 从 NEO4J_URI 中解析主机和端口
        # NEO4J_URI 格式: bolt://localhost:7687
        from urllib.parse import urlparse
        parsed = urlparse(settings.NEO4J_URI)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 7687
        
        # 构建连接URL
        # Neomodel需要的格式: bolt://username:password@host:port
        connection_url = f"bolt://{settings.NEO4J_USERNAME}:{settings.NEO4J_PASSWORD}@{host}:{port}"
        
        # 设置数据库URL
        neomodel_config.DATABASE_URL = connection_url
        
        # 设置数据库名称（如果不是默认的neo4j）
        if settings.NEO4J_DATABASE != "neo4j":
            neomodel_config.DATABASE_NAME = settings.NEO4J_DATABASE
        
        # 测试连接
        db.cypher_query("RETURN 1")
        
        logger.info(f"✅ Neomodel 连接成功: {host}:{port}")
        
    except Exception as e:
        logger.error(f"❌ Neomodel 连接失败: {str(e)}")
        raise


def create_constraints_and_indexes():
    """
    创建必要的约束和索引
    在应用启动时调用
    """
    try:
        # 这里会在实际模型定义后自动创建
        # Neomodel会根据模型定义自动管理索引
        logger.info("索引和约束将在模型首次使用时自动创建")
    except Exception as e:
        logger.error(f"创建索引失败: {str(e)}")


def get_db():
    """
    获取数据库连接（用于直接执行Cypher查询）
    """
    return db


class NeomodelTransaction:
    """
    Neomodel事务管理器
    提供事务支持
    """
    
    def __enter__(self):
        """开始事务"""
        db.begin()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """结束事务"""
        if exc_type is None:
            db.commit()
        else:
            db.rollback()
        return False
    
    def commit(self):
        """提交事务"""
        db.commit()
    
    def rollback(self):
        """回滚事务"""
        db.rollback()


def transaction():
    """
    获取事务上下文管理器
    
    使用示例:
    ```python
    with transaction():
        person1.save()
        person2.save()
        # 如果任何操作失败，所有操作都会回滚
    ```
    """
    return NeomodelTransaction()


# 在模块导入时初始化连接
# 注意：这应该在应用启动时调用，而不是在导入时
# 为了避免在测试或其他场景中自动连接，我们提供一个显式的初始化函数
def setup_neomodel():
    """
    设置Neomodel（应在应用启动时调用）
    """
    init_neomodel()
    create_constraints_and_indexes()