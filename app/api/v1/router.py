from fastapi import APIRouter
from .endpoints import auth
from .admin import admin_router

api_router = APIRouter()

# 包含认证路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)

# 包含管理后台路由
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["管理后台"]
) 