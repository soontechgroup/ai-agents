from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import math
import json

from app.schemas.conversation import *
from app.schemas.common import SuccessResponse
from app.schemas.CommonResponse import PaginationMeta
from app.services.conversation_service import ConversationService
from app.core.database import get_db
from app.core.models import User
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil
from app.services.langgraph_service import LangGraphService

router = APIRouter()


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """获取对话服务实例"""
    return ConversationService(db)


@router.post("/conversations", response_model=SuccessResponse[ConversationResponse], summary="创建对话")
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    创建新对话
    
    - **digital_human_id**: 数字人模板ID（必填）
    - **title**: 对话标题（可选，默认生成）
    """
    try:
        conversation = conversation_service.create_conversation(
            conversation_data, current_user.id
        )
        return ResponseUtil.success(data=conversation, message="对话创建成功")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/conversations", response_model=ConversationPageResponse, summary="分页获取对话列表")
async def get_conversations(
    page: int = 1,
    size: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    分页获取用户对话列表
    
    - **page**: 页码，从1开始（默认1）
    - **size**: 每页数量，最大100（默认10）
    - **search**: 搜索关键词，搜索标题（可选）
    - **status**: 过滤状态：active, archived, deleted（可选）
    """
    page_request = ConversationPageRequest(
        page=page,
        size=size,
        search=search,
        status=status
    )
    
    conversations, total = conversation_service.get_conversations_paginated(
        page_request, current_user.id
    )
    
    total_pages = math.ceil(total / size)
    
    pagination = PaginationMeta(
        page=page,
        size=size,
        total=total,
        pages=total_pages
    )
    
    return ConversationPageResponse(
        code=200,
        message="获取对话列表成功",
        data=conversations,
        pagination=pagination
    )


@router.get("/conversations/{conversation_id}", response_model=SuccessResponse[ConversationResponse], summary="获取对话详情")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取对话详情
    
    - **conversation_id**: 对话ID
    """
    conversation = conversation_service.get_conversation_by_id(
        conversation_id, current_user.id
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(data=conversation, message="获取对话详情成功")


@router.put("/conversations/{conversation_id}", response_model=SuccessResponse[ConversationResponse], summary="更新对话")
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新对话信息
    
    - **conversation_id**: 对话ID
    - **title**: 对话标题（可选）
    - **status**: 对话状态（可选）
    """
    conversation = conversation_service.update_conversation(
        conversation_id, conversation_data, current_user.id
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(data=conversation, message="对话更新成功")


@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse[None], summary="删除对话")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    删除对话（软删除）
    
    - **conversation_id**: 对话ID
    """
    success = conversation_service.delete_conversation(
        conversation_id, current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(message="对话删除成功")


@router.get("/conversations/{conversation_id}/messages", response_model=SuccessResponse[ConversationWithMessages], summary="获取对话消息")
async def get_conversation_messages(
    conversation_id: int,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取对话的所有消息
    
    - **conversation_id**: 对话ID  
    - **limit**: 消息数量限制（可选）
    """
    conversation_with_messages = conversation_service.get_conversation_with_messages(
        conversation_id, current_user.id, limit
    )
    
    if not conversation_with_messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(
        data=conversation_with_messages,
        message="获取对话消息成功"
    )


@router.post("/conversations/{conversation_id}/messages", response_model=SuccessResponse[MessageResponse], summary="发送消息")
async def send_message(
    conversation_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    发送消息（同步模式）
    
    - **conversation_id**: 对话ID
    - **content**: 消息内容
    """
    try:
        message = conversation_service.send_message(
            conversation_id, message_data.content, current_user.id
        )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        return ResponseUtil.success(data=message, message="消息发送成功")
        
    except ValueError as e:
        # 处理API密钥错误和其他LangGraph服务错误
        error_msg = str(e)
        if "invalid" in error_msg.lower() and "api" in error_msg.lower() and "key" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI服务配置错误，请联系管理员"
            )
        elif "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI服务请求过于频繁，请稍后再试"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"消息发送失败: {error_msg}"
            )


@router.post("/conversations/{conversation_id}/chat", summary="流式聊天")
async def chat_stream(
    conversation_id: int,
    chat_request: ChatStreamRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    流式聊天
    
    - **conversation_id**: 对话ID
    - **message**: 用户消息内容
    - **stream**: 是否流式响应（默认true）
    
    返回Server-Sent Events流，包含以下类型的数据：
    - **message**: 用户消息确认
    - **token**: AI响应的token流
    - **done**: 响应完成
    - **error**: 错误信息
    """
    def generate():
        try:
            for chunk in conversation_service.send_message_stream(
                conversation_id, chat_request.message, current_user.id
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "content": f"聊天流式响应失败: {str(e)}"
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.delete("/conversations/{conversation_id}/messages", response_model=SuccessResponse[None], summary="清除对话历史")
async def clear_conversation_history(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    清除对话的所有消息历史
    
    - **conversation_id**: 对话ID
    """
    success = conversation_service.clear_conversation_history(
        conversation_id, current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(message="对话历史清除成功")


@router.get("/health", response_model=SuccessResponse, summary="检查AI服务状态")
async def check_ai_service_health():
    """
    检查AI服务健康状态
    
    检查项目：
    - OpenAI API连接状态
    - LangGraph服务状态
    """
    try:
        # 尝试初始化LangGraph服务来测试API密钥
        test_service = LangGraphService()
        
        return ResponseUtil.success(
            data={
                "status": "healthy",
                "openai_connection": "ok",
                "langgraph_service": "ok"
            },
            message="AI服务运行正常"
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() and "api" in error_msg.lower() and "key" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API密钥无效，请检查配置"
            )
        elif "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="OpenAI API访问频率限制"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI服务初始化失败: {error_msg}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI服务检查失败: {str(e)}"
        )