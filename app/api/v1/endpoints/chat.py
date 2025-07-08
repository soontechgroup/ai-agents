from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
import logging
import json
from datetime import datetime

from app.schemas.chat import ChatRequest, ChatResponse, ChatSettings, ChatMessage
from app.schemas.common import SuccessResponse, ErrorResponse
from app.services.chat_service import chat_service
from app.utils.dependencies import get_current_user
from app.core.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/completion",
    response_model=SuccessResponse[ChatResponse],
    summary="聊天完成",
    description="发送消息给AI并获取回复"
)
async def chat_completion(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    创建聊天完成请求
    
    - **message**: 用户消息内容
    - **conversation_history**: 可选的对话历史记录
    - **model**: 可选的指定模型
    - **temperature**: 可选的温度参数(0.0-2.0)
    - **max_tokens**: 可选的最大token数量
    """
    try:
        logger.info(f"User {current_user.id} requesting chat completion")
        
        # 调用聊天服务
        response = await chat_service.create_chat_completion(request)
        
        return SuccessResponse(
            data=response,
            message="聊天完成成功"
        )
        
    except Exception as e:
        logger.error(f"Chat completion failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天请求失败: {str(e)}"
        )


@router.post(
    "/completion/stream",
    summary="流式聊天完成",
    description="发送消息给AI并获取流式回复"
)
async def chat_completion_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    创建流式聊天完成请求
    
    返回Server-Sent Events格式的流式响应
    """
    try:
        logger.info(f"User {current_user.id} requesting streaming chat completion")
        
        async def generate_response():
            try:
                async for chunk in chat_service.create_streaming_completion(request):
                    # 格式化为SSE事件
                    yield f"data: {json.dumps({'content': chunk, 'type': 'chunk'})}\n\n"
                
                # 发送结束信号
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming chat completion failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式聊天请求失败: {str(e)}"
        )


@router.get(
    "/models",
    response_model=SuccessResponse[List[str]],
    summary="获取可用模型",
    description="获取可用的AI模型列表"
)
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    """获取可用的AI模型列表"""
    try:
        models = chat_service.get_available_models()
        return SuccessResponse(
            data=models,
            message="获取模型列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get models for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.get(
    "/settings",
    response_model=SuccessResponse[ChatSettings],
    summary="获取聊天设置",
    description="获取当前的聊天配置设置"
)
async def get_chat_settings(
    current_user: User = Depends(get_current_user)
):
    """获取当前的聊天配置设置"""
    try:
        settings = ChatSettings()
        return SuccessResponse(
            data=settings,
            message="获取聊天设置成功"
        )
    except Exception as e:
        logger.error(f"Failed to get chat settings for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取聊天设置失败: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=SuccessResponse[dict],
    summary="验证API配置",
    description="验证OpenAI API密钥是否有效"
)
async def validate_api_configuration(
    current_user: User = Depends(get_current_user)
):
    """验证OpenAI API密钥是否有效"""
    try:
        is_valid = chat_service.validate_api_key()
        
        return SuccessResponse(
            data={
                "api_key_valid": is_valid,
                "timestamp": datetime.now().isoformat()
            },
            message="API配置验证成功" if is_valid else "API密钥无效"
        )
        
    except Exception as e:
        logger.error(f"API validation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API配置验证失败: {str(e)}"
        )


@router.post(
    "/quick-chat",
    response_model=SuccessResponse[ChatResponse],
    summary="快速聊天",
    description="发送单条消息进行快速聊天，无需提供对话历史"
)
async def quick_chat(
    message: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """
    快速聊天接口，适用于简单的单轮对话
    
    - **message**: 用户消息内容
    - **model**: 可选的指定模型
    - **temperature**: 可选的温度参数
    """
    try:
        logger.info(f"User {current_user.id} requesting quick chat")
        
        # 构建聊天请求
        request = ChatRequest(
            message=message,
            model=model,
            temperature=temperature
        )
        
        # 调用聊天服务
        response = await chat_service.create_chat_completion(request)
        
        return SuccessResponse(
            data=response,
            message="快速聊天成功"
        )
        
    except Exception as e:
        logger.error(f"Quick chat failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"快速聊天失败: {str(e)}"
        )
