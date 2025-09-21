from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.core.models import Base
from app.api.v1.router import api_router
from alembic.config import Config
from alembic import command
import time

from app.core.logger import logger, set_request_id

from app.core.mongodb import init_mongodb, close_mongodb

from app.core.neomodel_config import setup_neomodel

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="基于FastAPI的AI代理系统，包含JWT认证功能"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    request_id = set_request_id()
    
    logger.bind(request_id=request_id).info(f"📥 [{request_id}] 收到请求: {request.method} {request.url.path}")
    
    if request.url.query:
        logger.bind(request_id=request_id).debug(f"查询参数: {request.url.query}")
    
    if settings.DEBUG:
        logger.bind(request_id=request_id).debug(f"请求头: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        if response.status_code < 400:
            logger.bind(request_id=request_id).success(
                f"✅ [{request_id}] 请求完成: {request.method} {request.url.path} | "
                f"状态: {response.status_code} | 耗时: {process_time:.3f}s"
            )
        elif response.status_code < 500:
            logger.bind(request_id=request_id).warning(
                f"⚠️ [{request_id}] 客户端错误: {request.method} {request.url.path} | "
                f"状态: {response.status_code} | 耗时: {process_time:.3f}s"
            )
        else:
            logger.bind(request_id=request_id).error(
                f"❌ [{request_id}] 服务器错误: {request.method} {request.url.path} | "
                f"状态: {response.status_code} | 耗时: {process_time:.3f}s"
            )
        
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        logger.bind(request_id=request_id).error(
            f"💥 [{request_id}] 请求处理异常: {request.method} {request.url.path} | "
            f"耗时: {process_time:.3f}s | 异常: {type(e).__name__}: {str(e)}"
        )
        
        raise


@app.on_event("startup")
async def startup_event():
    max_retries = 2
    retry_interval = 1
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 尝试连接 MySQL 数据库 (第{attempt + 1}次尝试)")
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            logger.success("✅ MySQL 数据库连接成功!")
            
            try:
                logger.info("📦 开始执行数据库迁移...")
                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
                logger.success("✅ 数据库迁移完成!")
            except Exception as migration_error:
                logger.warning(f"⚠️ 数据库迁移失败: {migration_error}")
                logger.info("🔧 尝试使用 SQLAlchemy 创建表结构...")
                Base.metadata.create_all(bind=engine)
                logger.success("✅ 数据库表结构同步完成!")
            
            break
        except Exception as e:
            logger.warning(f"⚠️ MySQL 数据库连接失败: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ 等待 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)
            else:
                logger.error("❌ MySQL 数据库连接失败，已达到最大重试次数")
                raise
    
    try:
        logger.info("🔄 正在初始化 MongoDB...")
        await init_mongodb(
            mongodb_url=settings.MONGODB_URL,
            database_name=settings.MONGODB_DATABASE,
            document_models=[]
        )
        logger.success("✅ MongoDB 初始化成功!")
    except Exception as e:
        logger.error(f"❌ MongoDB 初始化失败: {e}")
        logger.warning("⚠️ 应用将继续运行，但 MongoDB 相关功能将不可用")
    
    try:
        logger.info("🔄 正在初始化 Neo4j (Neomodel)...")
        setup_neomodel()
        logger.success("✅ Neo4j Neomodel 初始化成功!")
    except Exception as e:
        logger.error(f"❌ Neo4j Neomodel 初始化失败: {e}")
        logger.warning("⚠️ 应用将继续运行，但图数据库功能将不可用")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🔄 正在关闭 MongoDB 连接...")
    await close_mongodb()
    logger.info("✅ MongoDB 连接已关闭")


app.include_router(api_router, prefix="/api/v1")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse('static/index.html')
