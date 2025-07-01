from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, protected

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# 用户管理路由
api_router.include_router(users.router, prefix="/user", tags=["users"])

# 受保护的路由
api_router.include_router(protected.router, prefix="/protected", tags=["protected"])
