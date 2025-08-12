from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv

# 获取环境变量，默认为开发环境
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# 根据环境变量加载对应的配置文件
def load_env_file():
    """根据环境变量加载对应的配置文件"""
    env_files = {
        "dev": ".env.dev",
        "development": ".env.dev"
    }
    
    # 获取对应环境的配置文件
    env_file = env_files.get(ENVIRONMENT.lower())
    
    if env_file and os.path.exists(env_file):
        print(f"🔧 加载环境配置文件: {env_file}")
        load_dotenv(env_file)
    else:
        print(f"⚠️  环境配置文件不存在: {env_file}，使用默认配置")
        # 尝试加载默认的 .env 文件
        if os.path.exists(".env"):
            print("🔧 加载默认配置文件: .env")
            load_dotenv(".env")

# 加载环境配置
load_env_file()


class Settings(BaseSettings):
    # JWT配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置 (与 docker-compose.yml 匹配)
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/ai_agents"
    
    # MongoDB 配置
    MONGODB_URL: str = "mongodb://admin:password123@localhost:27018/?authSource=admin"
    MONGODB_DATABASE: str = "ai_agents"
    
    # 应用配置
    PROJECT_NAME: str = "AI Agents API"
    VERSION: str = "1.0.0"
    
    # 环境配置
    ENVIRONMENT: str = ENVIRONMENT
    DEBUG: bool = True

    # 可选配置
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "logs"
    LOG_ROTATION: str = "00:00"
    LOG_RETENTION: str = "30 days"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Chroma 数据库配置
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "default_collection"

    class Config:
        # 不在这里指定 env_file，因为我们已经手动加载了
        env_file_encoding = 'utf-8'


# 创建配置实例
settings = Settings()

# 打印当前环境信息
print(f"🚀 当前运行环境: {settings.ENVIRONMENT}")
print(f"📊 调试模式: {'开启' if settings.DEBUG else '关闭'}")
print(f"🔗 MySQL 数据库: {settings.DATABASE_URL}")
print(f"🔗 MongoDB 数据库: {settings.MONGODB_URL}")