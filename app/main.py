from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.core.models import Base
from app.api.v1.router import api_router
import os
import time
import logging

# 配置日志
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="基于FastAPI的AI代理系统，包含JWT认证功能"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    max_retries = 10
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to initialize database (attempt {attempt + 1})")
            # Create database tables
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialization successful!")
            break
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Waiting {retry_interval} seconds before retry...")
                time.sleep(retry_interval)
            else:
                logger.error("Database initialization failed, maximum retries reached")
                raise


# 包含API路由
app.include_router(api_router, prefix="/api/v1")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """返回欢迎页面"""
    return FileResponse('static/index.html')
