from fastapi import APIRouter
from .endpoints import auth

# 创建管理后台路由
admin_router = APIRouter()

# 注册认证模块路由
admin_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["管理-认证"]
)

# 后续添加其他模块路由
# admin_router.include_router(users.router, prefix="/users", tags=["管理-用户"])
# admin_router.include_router(agents.router, prefix="/agents", tags=["管理-代理"])