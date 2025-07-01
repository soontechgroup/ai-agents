from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
import os

# 数据库配置 - 默认使用MySQL，可通过环境变量覆盖
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Kevinisagod1.1@localhost:3306/userdb?charset=utf8mb4")

# 根据数据库类型设置不同的配置
if DATABASE_URL.startswith("sqlite"):
    # SQLite配置
    engine = create_engine(
        DATABASE_URL, 
        echo=False,
        connect_args={"check_same_thread": False}  # SQLite特定参数
    )
else:
    # MySQL或其他数据库配置
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

# 数据库模型
class User(Base):
    __tablename__ = "users"
    
    # 根据数据库类型设置不同的表配置
    if not DATABASE_URL.startswith("sqlite"):
        # MySQL配置 - 支持中文字符
        __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 根据数据库类型设置不同的字段配置
    if DATABASE_URL.startswith("sqlite"):
        # SQLite配置
        name = Column(String(100), nullable=False)
        email = Column(String(255), nullable=False, unique=True)
        gender = Column(String(10), nullable=False)
    else:
        # MySQL配置 - 支持中文字符
        name = Column(String(100, collation='utf8mb4_unicode_ci'), nullable=False)
        email = Column(String(255, collation='utf8mb4_unicode_ci'), nullable=False, unique=True)
        gender = Column(String(10, collation='utf8mb4_unicode_ci'), nullable=False)
    
    password = Column(String(255), nullable=False)

# 创建所有表
def create_tables():
    Base.metadata.create_all(bind=engine)

# 数据库依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 