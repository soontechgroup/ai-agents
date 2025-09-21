# MySQL 关系型数据库

## 📚 使用说明

项目使用 MySQL 8.0 作为主要的关系型数据库，存储用户信息、系统配置等结构化数据。

## 🛠 数据库配置

### Docker 启动
```bash
# 启动所有数据库服务
docker-compose up -d

# 查看运行状态
docker-compose ps
```

### 连接信息
- **主机**: localhost
- **端口**: 3306
- **用户名**: root
- **密码**: 123456
- **数据库**: ai_agents

### 数据库连接
```python
# SQLAlchemy 连接配置
DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/ai_agents"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 同步引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Python 使用示例
```python
# 数据库连接配置
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/ai_agents"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Repository 层封装
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, user_data: dict):
        db_user = User(**user_data)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
```
