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
        "development": ".env.dev", 
        "test": ".env.test",
        "staging": ".env.staging",
        "prod": ".env.prod",
        "production": ".env.prod"
    }
    
    # 获取对应环境的配置文件
    env_file = env_files.get(ENVIRONMENT.lower())
    
    if env_file and os.path.exists(env_file):
        print(f"[CONFIG] Loading environment config file: {env_file}")
        load_dotenv(env_file)
    else:
        print(f"[WARNING] Environment config file not found: {env_file}, using default config")
        # Try to load default .env file
        if os.path.exists(".env"):
            print("[CONFIG] Loading default config file: .env")
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
    
    # 应用配置
    PROJECT_NAME: str = "AI Agents API"
    VERSION: str = "1.0.0"
    
    # 环境配置
    ENVIRONMENT: str = ENVIRONMENT
    DEBUG: bool = True

    # 可选配置
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS: int = 2048
    OPENAI_TEMPERATURE: float = 0.7

    class Config:
        # 不在这里指定 env_file，因为我们已经手动加载了
        env_file_encoding = 'utf-8'


# 创建配置实例
settings = Settings()

# Print current environment info
print(f"[STARTUP] Current environment: {settings.ENVIRONMENT}")
print(f"[DEBUG] Debug mode: {'enabled' if settings.DEBUG else 'disabled'}")
print(f"[DATABASE] Database connection: {settings.DATABASE_URL}")