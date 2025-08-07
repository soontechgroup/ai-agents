from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.core.models import Base  # 移到顶部导入
from app.api.v1.router import api_router
from alembic.config import Config
from alembic import command
import os
import time
import logging
import traceback

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求和响应"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"收到请求: {request.method} {request.url.path}")
    if request.url.query:
        logger.debug(f"查询参数: {request.url.query}")
    
    try:
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录响应信息
        logger.info(f"请求完成: {request.method} {request.url.path} - 状态码: {response.status_code} - 耗时: {process_time:.3f}s")
        
        # 如果是错误响应，记录更多信息
        if response.status_code >= 400:
            logger.warning(f"错误响应: {request.method} {request.url.path} - 状态码: {response.status_code}")
        
        return response
    except Exception as e:
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录异常详情
        logger.error(f"请求处理异常: {request.method} {request.url.path} - 耗时: {process_time:.3f}s")
        logger.error(f"异常类型: {type(e).__name__}")
        logger.error(f"异常信息: {str(e)}")
        logger.error(f"异常堆栈:\n{traceback.format_exc()}")
        
        # 重新抛出异常，让FastAPI处理
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    # 记录未处理的异常
    logger.error(f"未处理异常 - 路径: {request.url.path}")
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常信息: {str(exc)}")
    logger.error(f"完整堆栈:\n{traceback.format_exc()}")
    
    # 返回友好的错误响应
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "内部服务器错误",
            "detail": str(exc) if settings.DEBUG else "服务器处理请求时发生错误"
        }
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
            
            # 使用 Alembic 自动执行数据库迁移
            try:
                logger.info("开始执行数据库迁移...")
                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
                logger.info("✅ 数据库迁移完成!")
            except Exception as migration_error:
                logger.warning(f"数据库迁移失败: {migration_error}")
                # 如果迁移失败，尝试使用原来的方式创建表（用于首次部署）
                logger.info("尝试使用 SQLAlchemy 创建表结构...")
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
