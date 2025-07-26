from fastapi import APIRouter
from .endpoints import auth, digital_humans, user
from .admin import admin_router

api_router = APIRouter()

# 包含认证路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)

# 包含数字人路由
api_router.include_router(
    digital_humans.router,
    prefix="/digital-humans",
    tags=["数字人"]
)

# 包含用户路由
api_router.include_router(
    user.router,
    tags=["用户"]
)

# 包含管理后台路由
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["管理后台"]
) 