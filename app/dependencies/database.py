"""数据库相关依赖"""
from app.core.database import SessionLocal


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()