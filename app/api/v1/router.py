from fastapi import APIRouter
from .endpoints import auth, chat

api_router = APIRouter()

# 包含认证路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)

# 包含聊天路由
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["智能对话"]
) 