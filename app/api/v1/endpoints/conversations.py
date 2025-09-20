from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import math
import json

from app.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationPageRequest, ConversationPageResponse,
    MessageResponse, ConversationWithMessages,
    ConversationDetailRequest, ConversationUpdateRequest,
    ConversationDeleteRequest, ConversationMessagesRequest,
    ConversationSendRequest, ConversationChatRequest,
    ConversationClearRequest
)
from app.schemas.common_response import SuccessResponse
from app.schemas.common_response import PaginationMeta
from app.services.conversation_service import ConversationService
from app.core.database import get_db
from app.dependencies.services import get_conversation_service
from app.core.models import User
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil

router = APIRouter()


@router.post("/create", response_model=SuccessResponse[ConversationResponse], summary="创建对话")
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
    conversation = conversation_service.create_conversation(
        conversation_data, current_user.id
    )
    return ResponseUtil.success(data=conversation, message="对话创建成功")


@router.post("/page", response_model=ConversationPageResponse, summary="分页获取对话列表")
async def get_conversations(
    request: ConversationPageRequest,
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
    conversations, total = conversation_service.get_conversations_paginated(
        request, current_user.id
    )
    
    total_pages = math.ceil(total / request.size)
    
    pagination = PaginationMeta(
        page=request.page,
        size=request.size,
        total=total,
        pages=total_pages
    )
    
    return ConversationPageResponse(
        code=200,
        message="获取对话列表成功",
        data=conversations,
        pagination=pagination
    )


@router.post("/detail", response_model=SuccessResponse[ConversationResponse], summary="获取对话详情")
async def get_conversation(
    request: ConversationDetailRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取对话详情

    - **digital_human_id**: 数字人ID
    """
    thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
    conversation = conversation_service.get_conversation_by_thread_id(
        thread_id, current_user.id
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(data=conversation, message="获取对话详情成功")


@router.post("/update", response_model=SuccessResponse[ConversationResponse], summary="更新对话")
async def update_conversation(
    request: ConversationUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新对话信息

    - **digital_human_id**: 数字人ID
    - **title**: 对话标题（可选）
    """
    thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
    # 将ConversationUpdateRequest转换为ConversationUpdate（不包含digital_human_id）
    update_data = ConversationUpdate(**request.model_dump(exclude={'digital_human_id'}))
    conversation = conversation_service.update_conversation(
        thread_id, update_data, current_user.id
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(data=conversation, message="对话更新成功")


@router.post("/delete", response_model=SuccessResponse[None], summary="删除对话")
async def delete_conversation(
    request: ConversationDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    删除对话（软删除）

    - **digital_human_id**: 数字人ID
    """
    thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
    success = conversation_service.delete_conversation(
        thread_id, current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(message="对话删除成功")


@router.post("/messages", response_model=SuccessResponse[ConversationWithMessages], summary="获取对话消息")
async def get_conversation_messages(
    request: ConversationMessagesRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取对话的所有消息

    - **digital_human_id**: 数字人ID
    - **limit**: 消息数量限制（可选）
    """
    thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
    conversation_with_messages = conversation_service.get_conversation_with_messages(
        thread_id, current_user.id, request.limit
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


@router.post("/send", response_model=SuccessResponse[MessageResponse], summary="发送消息")
async def send_message(
    request: ConversationSendRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    发送消息（同步模式）

    - **digital_human_id**: 数字人ID
    - **content**: 消息内容
    """
    try:
        thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
        message = conversation_service.send_message(
            thread_id, request.content, current_user.id
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


@router.post("/chat", summary="流式聊天")
async def chat_stream(
    request: ConversationChatRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    流式聊天

    - **digital_human_id**: 数字人ID
    - **message**: 用户消息内容
    - **stream**: 是否流式响应（默认true）

    返回Server-Sent Events流，包含以下类型的数据：
    - **message**: 用户消息确认
    - **memory**: 记忆搜索结果（前端应展示为状态提示，如"正在查找相关记忆..."）
    - **token**: AI响应的token流
    - **done**: 响应完成
    - **error**: 错误信息

    注意：前端应该根据 type 字段优雅地展示不同类型的消息，
    而不是直接显示 JSON 字符串
    """
    def generate():
        thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
        for chunk in conversation_service.send_message_stream(
            thread_id, request.message, current_user.id
        ):
            yield f"data: {chunk}\n\n"

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


@router.post("/clear", response_model=SuccessResponse[None], summary="清除对话历史")
async def clear_conversation_history(
    request: ConversationClearRequest,
    current_user: User = Depends(get_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    清除对话的所有消息历史

    - **digital_human_id**: 数字人ID
    """
    thread_id = f"chat_{request.digital_human_id}_{current_user.id}"
    success = conversation_service.clear_conversation_history(
        thread_id, current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return ResponseUtil.success(message="对话历史清除成功")


