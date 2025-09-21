# PyMySQL 数据库驱动

## 📚 使用说明

项目使用 PyMySQL 作为 SQLAlchemy 的 MySQL 驱动，提供与 MySQL 数据库的连接。

## 🛠 安装配置

### 安装依赖
```bash
pip install pymysql
```

### 数据库连接
```python
# app/core/config.py
DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/ai_agents"
```

## 💻 项目应用

### SQLAlchemy 集成
```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# PyMySQL 作为 SQLAlchemy 的驱动
# URL 格式: mysql+pymysql://user:password@host:port/database
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 连接健康检查
    pool_recycle=3600,   # 连接回收时间
    echo=False           # 生产环境关闭 SQL 日志
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

### 连接池配置
```python
# app/core/database.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    pool_timeout=30,     # 获取连接超时时间
    pool_recycle=3600,   # 连接回收时间（秒）
    pool_pre_ping=True   # 连接健康检查
)
```

### 依赖注入
```python
# app/dependencies/database.py
from app.core.database import SessionLocal

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 在 API 端点中使用
@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

PyMySQL 为项目提供了稳定可靠的 MySQL 连接驱动，与 SQLAlchemy ORM 完美集成。