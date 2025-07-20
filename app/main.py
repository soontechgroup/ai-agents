from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.core.models import Base  # 移到顶部导入
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
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """应用启动时检查数据库连接"""
    max_retries = 2
    retry_interval = 1
    
    for attempt in range(max_retries):
        try:
            logger.info(f"尝试连接数据库 (第{attempt + 1}次尝试)")
            # 测试数据库连接
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            logger.info("数据库连接成功!")
            
            # 自动创建/更新表结构（类似 GORM 的 AutoMigrate）
            logger.info("开始自动同步数据库表结构...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ 数据库表结构同步完成!")
            
            break
        except Exception as e:
            logger.warning(f"数据库连接失败: {e}")
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)
            else:
                logger.error("数据库连接失败，已达到最大重试次数")
                raise


# 包含API路由
app.include_router(api_router, prefix="/api/v1")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """返回欢迎页面"""
    return FileResponse('static/index.html')
