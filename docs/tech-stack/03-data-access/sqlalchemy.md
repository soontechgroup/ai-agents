# SQLAlchemy ORM框架

## 📚 使用说明

项目使用 SQLAlchemy 作为 ORM（对象关系映射）框架，提供类型安全的数据库操作。

## 🛠 框架配置

### 安装依赖
```bash
pip install sqlalchemy pymysql
```

### 数据库配置
```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 创建数据库引擎
engine = create_engine(
    "mysql+pymysql://root:123456@localhost:3306/ai_agents",
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()

# 依赖注入：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 基本使用示例
```python
# 模型定义
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系定义
    digital_humans = relationship("DigitalHuman", back_populates="owner")

class DigitalHuman(Base):
    __tablename__ = "digital_humans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    owner_id = Column(Integer, ForeignKey("users.id"))
    personality = Column(JSON)

    # 关系定义
    owner = relationship("User", back_populates="digital_humans")

# 基本操作
def create_user(username: str, email: str, hashed_password: str):
    db = SessionLocal()
    try:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()

def get_user_with_digital_humans(user_id: int):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()
```

## 💻 项目应用

### 核心模型定义
```python
# app/core/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    digital_humans = relationship("DigitalHuman", back_populates="owner")

class DigitalHuman(Base):
    __tablename__ = "digital_humans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    type = Column(String(50), default="专业助手")
    skills = Column(JSON)
    personality = Column(JSON)
    owner_id = Column(Integer, ForeignKey("users.id"))

    # 关系
    owner = relationship("User", back_populates="digital_humans")
    training_messages = relationship("DigitalHumanTrainingMessage", back_populates="digital_human")
```


SQLAlchemy 为项目提供强大的 ORM 功能，支持复杂的关系映射和类型安全的数据库操作。