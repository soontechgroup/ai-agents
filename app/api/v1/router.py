from fastapi import APIRouter
from .endpoints import (
    auth, 
    digital_humans, 
    user, 
    conversations, 
    chroma,
    search
)
from .admin import admin_router

api_router = APIRouter()

# 包含认证路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)

# 包含数字人模板路由
api_router.include_router(
    digital_humans.router,
    prefix="/digital-humans",
    tags=["数字人模板"]
)

# 包含对话路由（独立路径）
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["对话管理"]
)

# 包含用户路由
api_router.include_router(
    user.router,
    prefix="/users",
    tags=["用户管理"]
)

# 包含 Chroma 数据库路由
api_router.include_router(
    chroma.router,
    prefix="/chroma",
    tags=["Chroma 向量数据库"]
)

# 包含混合搜索路由
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["混合搜索"]
)

# 包含管理后台路由
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["管理后台"]
) 