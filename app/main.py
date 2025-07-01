from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1 import api_router
from app.core.database import create_tables
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表
    create_tables()
    yield
    # 关闭时的清理工作（如果需要）

app = FastAPI(
    title="AI Agents API", 
    description="AI Agents管理系统，包含用户管理和JWT认证",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 包含API路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """返回欢迎页面"""
    return FileResponse('static/index.html')
