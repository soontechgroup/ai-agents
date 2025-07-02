from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # JWT配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/ai_agents"
    
    # 应用配置
    PROJECT_NAME: str = "AI Agents API"
    VERSION: str = "1.0.0"
    
    class Config:
        env_file = ".env"


# 创建配置实例
settings = Settings() 