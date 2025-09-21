# PyMySQL 数据库驱动

## 📚 概念介绍

PyMySQL 是一个纯 Python 实现的 MySQL 客户端库，提供了对 MySQL 数据库的连接和操作功能。它是 MySQLdb（MySQL-python）的纯 Python 替代品，无需编译依赖，支持 Python 3.x，并且与 SQLAlchemy 等 ORM 框架完美兼容。

**核心特性：**
- **纯 Python 实现**：无需 C 扩展，安装简单，跨平台兼容
- **DB-API 2.0 兼容**：遵循 Python 数据库 API 规范
- **MySQL 协议支持**：完整支持 MySQL 通信协议
- **连接池支持**：高效的数据库连接管理
- **安全特性**：支持 SSL 连接和参数化查询

## 🎯 核心作用

### 1. 数据库连接桥梁
- 建立 Python 应用与 MySQL 数据库的通信通道
- 提供底层数据库操作的接口和协议实现
- 处理网络通信和数据传输

### 2. SQL 执行引擎
- 执行 SQL 查询和数据操作命令
- 管理事务和连接状态
- 处理结果集和数据类型转换

### 3. ORM 框架基础
- 作为 SQLAlchemy 的底层驱动
- 提供异步操作支持（通过 aiomysql）
- 支持连接池和性能优化

### 4. 数据安全保障
- 实现 SQL 注入防护
- 支持加密连接和认证
- 提供参数化查询机制

## 🔄 使用前后对比

### 使用前：原生 MySQL 操作
```python
# 使用 mysql-connector-python 或其他驱动
import mysql.connector
from mysql.connector import Error

class LegacyMySQLConnection:
    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
        except Error as e:
            print(f"数据库连接失败: {e}")

    def execute_query(self, query, params=None):
        """执行查询"""
        if not self.connection.is_connected():
            self.connect()

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                self.connection.commit()
                return cursor.rowcount
        except Error as e:
            self.connection.rollback()
            print(f"查询执行失败: {e}")
            return None
        finally:
            cursor.close()

    def close(self):
        """关闭连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()

# 使用示例
db = LegacyMySQLConnection('localhost', 'testdb', 'user', 'password')
users = db.execute_query("SELECT * FROM users WHERE age > %s", (18,))

# 问题：
# 1. 手动连接管理，容易出现连接泄漏
# 2. 没有连接池，性能较差
# 3. 错误处理复杂
# 4. 不支持现代异步编程模式
# 5. 与 ORM 框架集成困难
```

### 使用后：PyMySQL + SQLAlchemy 现代方案
```python
# PyMySQL + SQLAlchemy 现代数据访问
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

class ModernDatabaseService:
    def __init__(self, database_url: str):
        # 同步引擎
        self.sync_engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        # 异步引擎
        self.async_engine = create_async_engine(
            database_url.replace("mysql+pymysql://", "mysql+aiomysql://"),
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        # 会话工厂
        self.async_session_factory = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def get_session(self):
        """获取数据库会话"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def execute_query(self, query: str, params: dict = None):
        """执行查询"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()

    async def execute_update(self, query: str, params: dict = None):
        """执行更新"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            return result.rowcount

# 使用示例
db_service = ModernDatabaseService('mysql+pymysql://user:password@localhost/testdb')

async def get_users_by_age(min_age: int):
    return await db_service.execute_query(
        "SELECT * FROM users WHERE age > :min_age",
        {"min_age": min_age}
    )

# 优势：
# 1. 自动连接池管理
# 2. 异步支持，高并发性能
# 3. 简洁的 API 和错误处理
# 4. 与 ORM 框架无缝集成
# 5. 生产级别的性能和可靠性
```

## 🏆 行业最佳实践

### 1. 连接池配置优化
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import pymysql

def create_optimized_engine(database_url: str):
    """创建优化的数据库引擎"""
    return create_engine(
        database_url,
        # 连接池配置
        poolclass=QueuePool,
        pool_size=20,          # 连接池大小
        max_overflow=0,        # 最大溢出连接数
        pool_pre_ping=True,    # 连接前检查
        pool_recycle=3600,     # 连接回收时间(秒)

        # PyMySQL 特定配置
        connect_args={
            "charset": "utf8mb4",
            "use_unicode": True,
            "autocommit": False,
            "connect_timeout": 10,
            "read_timeout": 30,
            "write_timeout": 30,

            # SSL 配置
            "ssl_disabled": False,
            "ssl_verify_cert": True,

            # 性能优化
            "sql_mode": "STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },

        # 引擎级配置
        echo=False,            # 是否打印 SQL
        future=True,           # 使用 SQLAlchemy 2.0 API
    )

# 异步引擎配置
async def create_async_optimized_engine(database_url: str):
    """创建优化的异步数据库引擎"""
    # 替换驱动为 aiomysql
    async_url = database_url.replace("mysql+pymysql://", "mysql+aiomysql://")

    return create_async_engine(
        async_url,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=3600,

        connect_args={
            "charset": "utf8mb4",
            "autocommit": False,
            "connect_timeout": 10,

            # 异步特定配置
            "echo": False,
            "server_public_key": None,
        }
    )
```

### 2. 连接管理最佳实践
```python
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import logging

class DatabaseConnectionManager:
    def __init__(self, engine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """获取数据库会话 - 最佳实践"""
        session = AsyncSession(self.engine)
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self.logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """数据库健康检查"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            self.logger.error(f"数据库健康检查失败: {e}")
            return False

    async def test_connection_pool(self):
        """测试连接池性能"""
        start_time = time.time()

        async def test_query():
            async with self.get_session() as session:
                await session.execute(text("SELECT SLEEP(0.1)"))

        # 并发测试
        tasks = [test_query() for _ in range(50)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        self.logger.info(f"连接池测试完成，耗时: {end_time - start_time:.2f}秒")

    async def get_connection_info(self) -> dict:
        """获取连接信息"""
        async with self.get_session() as session:
            result = await session.execute(text("""
                SELECT
                    CONNECTION_ID() as connection_id,
                    DATABASE() as current_database,
                    USER() as current_user,
                    VERSION() as mysql_version
            """))

            row = result.fetchone()
            return {
                "connection_id": row.connection_id,
                "database": row.current_database,
                "user": row.current_user,
                "mysql_version": row.mysql_version
            }
```

### 3. 事务管理策略
```python
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging

class TransactionManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def transaction(self, isolation_level: str = None):
        """事务管理上下文"""
        session = self.session_factory()

        if isolation_level:
            await session.execute(
                text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
            )

        try:
            await session.begin()
            yield session
            await session.commit()
            self.logger.debug("事务提交成功")

        except Exception as e:
            await session.rollback()
            self.logger.error(f"事务回滚: {e}")
            raise

        finally:
            await session.close()

    async def batch_operation(self, operations: list, batch_size: int = 1000):
        """批量操作事务管理"""
        total_processed = 0

        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]

            async with self.transaction() as session:
                for operation in batch:
                    await operation(session)

                total_processed += len(batch)
                self.logger.info(f"批量处理进度: {total_processed}/{len(operations)}")

        return total_processed

    @asynccontextmanager
    async def read_only_transaction(self):
        """只读事务"""
        async with self.transaction() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session

    @asynccontextmanager
    async def serializable_transaction(self):
        """可串行化事务"""
        async with self.transaction("SERIALIZABLE") as session:
            yield session
```

### 4. 错误处理和重试机制
```python
import asyncio
from functools import wraps
from sqlalchemy.exc import DisconnectionError, OperationalError
import pymysql.err

class DatabaseErrorHandler:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)

    def retry_on_disconnect(self, func):
        """连接断开重试装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except (DisconnectionError, OperationalError, pymysql.err.OperationalError) as e:
                    last_exception = e

                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** attempt)
                        self.logger.warning(
                            f"数据库连接失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"数据库连接重试失败，放弃操作: {e}")

            raise last_exception

        return wrapper

    def handle_mysql_errors(self, func):
        """MySQL 错误处理装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except pymysql.err.IntegrityError as e:
                if e.args[0] == 1062:  # Duplicate entry
                    self.logger.warning(f"数据重复: {e}")
                    raise ValueError("数据已存在")
                elif e.args[0] == 1452:  # Foreign key constraint
                    self.logger.warning(f"外键约束违反: {e}")
                    raise ValueError("外键约束错误")
                else:
                    raise

            except pymysql.err.DataError as e:
                self.logger.error(f"数据格式错误: {e}")
                raise ValueError("数据格式不正确")

            except pymysql.err.ProgrammingError as e:
                self.logger.error(f"SQL语法错误: {e}")
                raise ValueError("SQL 语句错误")

        return wrapper

# 使用示例
class UserRepository:
    def __init__(self, db_manager, error_handler):
        self.db_manager = db_manager
        self.error_handler = error_handler

    @DatabaseErrorHandler().retry_on_disconnect
    @DatabaseErrorHandler().handle_mysql_errors
    async def create_user(self, user_data: dict) -> int:
        """创建用户"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                text("""
                    INSERT INTO users (name, email, created_at)
                    VALUES (:name, :email, NOW())
                """),
                user_data
            )
            return result.lastrowid
```

## 💻 项目应用

### 1. 数据库配置和初始化
```python
# app/core/database.py
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 安装 PyMySQL 作为 MySQLdb 的替代
pymysql.install_as_MySQLdb()

class DatabaseManager:
    def __init__(self):
        self.sync_engine = None
        self.async_engine = None
        self.async_session_factory = None

    def init_database(self):
        """初始化数据库连接"""
        # 同步引擎（用于 Alembic 迁移）
        self.sync_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "charset": "utf8mb4",
                "use_unicode": True,
            }
        )

        # 异步引擎（用于应用程序）
        async_url = settings.DATABASE_URL.replace(
            "mysql+pymysql://",
            "mysql+aiomysql://"
        )

        self.async_engine = create_async_engine(
            async_url,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        # 异步会话工厂
        self.async_session_factory = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        """获取异步数据库会话"""
        async with self.async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def close_connections(self):
        """关闭数据库连接"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.sync_engine:
            self.sync_engine.dispose()

# 全局数据库管理器
db_manager = DatabaseManager()
```

### 2. 仓储层实现
```python
# app/repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update, delete
from app.core.database import db_manager

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    def __init__(self, model_class: type):
        self.model_class = model_class

    async def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取实体"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(self.model_class).where(self.model_class.id == id)
            )
            return result.scalar_one_or_none()

    async def create(self, entity_data: dict) -> T:
        """创建新实体"""
        async with db_manager.get_session() as session:
            entity = self.model_class(**entity_data)
            session.add(entity)
            await session.flush()
            await session.refresh(entity)
            return entity

    async def update(self, id: int, update_data: dict) -> Optional[T]:
        """更新实体"""
        async with db_manager.get_session() as session:
            await session.execute(
                update(self.model_class)
                .where(self.model_class.id == id)
                .values(**update_data)
            )

            # 获取更新后的实体
            result = await session.execute(
                select(self.model_class).where(self.model_class.id == id)
            )
            return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        """删除实体"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                delete(self.model_class).where(self.model_class.id == id)
            )
            return result.rowcount > 0

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """获取实体列表"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(self.model_class)
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()

# app/repositories/user_repository.py
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from sqlalchemy import text

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()

    async def get_active_users(self) -> List[User]:
        """获取活跃用户"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM users
                    WHERE is_active = true
                    AND last_login > DATE_SUB(NOW(), INTERVAL 30 DAY)
                    ORDER BY last_login DESC
                """)
            )
            return result.fetchall()

    async def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        async with db_manager.get_session() as session:
            await session.execute(
                text("""
                    UPDATE users
                    SET last_login = NOW()
                    WHERE id = :user_id
                """),
                {"user_id": user_id}
            )
```

### 3. 依赖注入集成
```python
# app/dependencies/database.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_manager
from app.repositories.user_repository import UserRepository

async def get_db_session() -> AsyncSession:
    """获取数据库会话依赖"""
    async with db_manager.get_session() as session:
        yield session

def get_user_repository() -> UserRepository:
    """获取用户仓储依赖"""
    return UserRepository()

# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db_session, get_user_repository
from app.repositories.user_repository import UserRepository

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """获取用户信息"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.post("/users")
async def create_user(
    user_data: dict,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """创建用户"""
    try:
        user = await user_repo.create(user_data)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 4. 数据库迁移集成
```python
# alembic/env.py
import asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import pymysql

# 安装 PyMySQL 作为 MySQLdb 的替代
pymysql.install_as_MySQLdb()

def run_migrations_online() -> None:
    """在线模式运行迁移"""
    configuration = context.config.get_section(context.config.config_ini_section)

    # 确保使用 PyMySQL 驱动
    configuration["sqlalchemy.url"] = configuration["sqlalchemy.url"].replace(
        "mysql://", "mysql+pymysql://"
    )

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        async with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await do_run_migrations(connection)
        await connectable.dispose()

    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## 📊 选择理由

### 1. 技术优势
- **纯 Python 实现**：无需编译依赖，部署简单
- **跨平台兼容**：支持 Windows、Linux、macOS
- **Python 3 原生**：完全支持现代 Python 特性
- **性能优良**：高效的网络通信和数据处理

### 2. 生态集成
- **SQLAlchemy 兼容**：作为主流 ORM 的推荐驱动
- **异步支持**：通过 aiomysql 支持异步操作
- **连接池**：与连接池框架无缝集成
- **工具支持**：与各种 Python 工具链兼容

### 3. 开发效率
- **安装简单**：pip install 即可，无需额外配置
- **调试友好**：纯 Python 实现，便于调试和问题排查
- **文档完善**：详细的文档和示例代码
- **社区活跃**：持续维护和更新

### 4. 生产可靠性
- **久经考验**：在大量生产环境中使用
- **稳定性好**：成熟的代码库，bug 较少
- **安全性**：支持 SSL 连接和参数化查询
- **监控支持**：与监控和日志系统集成良好

## 🚀 性能优化建议

### 1. 连接池优化
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def create_optimized_mysql_engine(database_url: str):
    """创建优化的 MySQL 引擎"""
    return create_engine(
        database_url,
        # 连接池配置
        poolclass=QueuePool,
        pool_size=20,              # 连接池大小
        max_overflow=0,            # 禁用溢出
        pool_pre_ping=True,        # 连接前检查
        pool_recycle=3600,         # 1小时回收连接

        # PyMySQL 优化参数
        connect_args={
            "charset": "utf8mb4",
            "use_unicode": True,
            "autocommit": False,

            # 超时设置
            "connect_timeout": 10,
            "read_timeout": 30,
            "write_timeout": 30,

            # 网络优化
            "client_flag": 0,
            "compress": True,         # 启用压缩

            # 缓冲区优化
            "max_allowed_packet": 16777216,  # 16MB

            # SQL 模式
            "sql_mode": "STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE",
        }
    )
```

### 2. 查询性能优化
```python
from sqlalchemy import text
from sqlalchemy.orm import selectinload, joinedload

class OptimizedQueryService:
    @staticmethod
    async def batch_select(session, model, ids: list, batch_size: int = 1000):
        """批量查询优化"""
        results = []

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]

            # 使用 IN 查询而不是多个单独查询
            result = await session.execute(
                select(model).where(model.id.in_(batch_ids))
            )
            results.extend(result.scalars().all())

        return results

    @staticmethod
    async def eager_loading_query(session, model, related_fields: list):
        """预加载关联查询"""
        query = select(model)

        # 添加预加载
        for field in related_fields:
            if hasattr(model, field):
                query = query.options(selectinload(getattr(model, field)))

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def paginated_query(
        session,
        model,
        page: int = 1,
        per_page: int = 20,
        order_by=None
    ):
        """分页查询优化"""
        offset = (page - 1) * per_page

        query = select(model).limit(per_page).offset(offset)

        if order_by:
            query = query.order_by(order_by)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def complex_aggregation(session):
        """复杂聚合查询优化"""
        # 使用原生 SQL 进行复杂聚合
        result = await session.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total_users,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users,
                AVG(CASE WHEN last_login IS NOT NULL
                    THEN TIMESTAMPDIFF(DAY, last_login, NOW())
                    END) as avg_days_since_login
            FROM users
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """))

        return [dict(row) for row in result.fetchall()]
```

### 3. 并发处理优化
```python
import asyncio
from asyncio import Semaphore
from sqlalchemy.ext.asyncio import AsyncSession

class ConcurrentDatabaseProcessor:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = Semaphore(max_concurrent)

    async def concurrent_operations(
        self,
        operations: list,
        session_factory
    ):
        """并发数据库操作"""

        async def limited_operation(operation):
            async with self.semaphore:
                async with session_factory() as session:
                    return await operation(session)

        tasks = [limited_operation(op) for op in operations]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def bulk_insert_optimized(
        self,
        session: AsyncSession,
        model,
        data_list: list,
        batch_size: int = 1000
    ):
        """优化的批量插入"""

        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]

            # 使用 bulk_insert_mappings 进行批量插入
            await session.execute(
                model.__table__.insert(),
                batch
            )

            # 定期提交以避免长事务
            if i % (batch_size * 10) == 0:
                await session.commit()

    async def bulk_update_optimized(
        self,
        session: AsyncSession,
        model,
        updates: list,
        batch_size: int = 1000
    ):
        """优化的批量更新"""

        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]

            # 构建批量更新语句
            cases = []
            ids = []

            for update in batch:
                cases.append(f"WHEN {update['id']} THEN '{update['value']}'")
                ids.append(update['id'])

            if cases:
                await session.execute(text(f"""
                    UPDATE {model.__tablename__}
                    SET value = CASE id {' '.join(cases)} END
                    WHERE id IN ({','.join(map(str, ids))})
                """))
```

### 4. 监控和诊断
```python
import time
import logging
from functools import wraps
from sqlalchemy import event
from sqlalchemy.engine import Engine

class DatabaseMonitor:
    def __init__(self):
        self.query_times = []
        self.slow_query_threshold = 1.0  # 1秒
        self.logger = logging.getLogger(__name__)

    def setup_query_monitoring(self, engine: Engine):
        """设置查询监控"""

        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()

        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time
            self.query_times.append(total)

            if total > self.slow_query_threshold:
                self.logger.warning(f"慢查询检测: {total:.2f}s - {statement[:100]}...")

    def monitor_connection_pool(self, engine: Engine):
        """监控连接池状态"""
        pool = engine.pool

        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }

    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        if not self.query_times:
            return {}

        return {
            "total_queries": len(self.query_times),
            "avg_query_time": sum(self.query_times) / len(self.query_times),
            "max_query_time": max(self.query_times),
            "min_query_time": min(self.query_times),
            "slow_queries": len([t for t in self.query_times if t > self.slow_query_threshold])
        }

    def query_performance_decorator(self, func):
        """查询性能监控装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                self.query_times.append(execution_time)

                if execution_time > self.slow_query_threshold:
                    self.logger.warning(f"慢操作检测: {func.__name__} 耗时 {execution_time:.2f}s")

                return result

            except Exception as e:
                self.logger.error(f"数据库操作失败: {func.__name__} - {e}")
                raise

        return wrapper
```

PyMySQL 作为项目的 MySQL 数据库驱动，提供了可靠、高效的数据库连接能力。通过合理的配置和优化，能够实现高性能的数据库访问，是构建现代 Python Web 应用的重要基础组件。