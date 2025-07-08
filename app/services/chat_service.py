import openai
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChatSettings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatService:
    """OpenAI聊天服务类"""
    
    def __init__(self):
        """初始化OpenAI客户端"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_settings = ChatSettings(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS
        )
        
    async def create_chat_completion(
        self, 
        request: ChatRequest,
        custom_settings: Optional[ChatSettings] = None
    ) -> ChatResponse:
        """
        创建聊天完成请求
        
        Args:
            request: 聊天请求对象
            custom_settings: 自定义设置（可选）
            
        Returns:
            ChatResponse: 聊天响应对象
            
        Raises:
            Exception: 当API调用失败时
        """
        try:
            # 使用自定义设置或默认设置
            settings_to_use = custom_settings or self.default_settings
            
            # 构建消息列表
            messages = self._build_messages(request, settings_to_use)
            
            # 获取模型参数
            model = request.model or settings_to_use.model
            temperature = request.temperature if request.temperature is not None else settings_to_use.temperature
            max_tokens = request.max_tokens or settings_to_use.max_tokens
            
            logger.info(f"Sending chat completion request with model: {model}")
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            # 提取响应内容
            ai_message = response.choices[0].message.content
            usage_info = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None
            
            logger.info(f"Chat completion successful, tokens used: {usage_info}")
            
            return ChatResponse(
                message=ai_message,
                model=model,
                usage=usage_info,
                timestamp=datetime.now()
            )
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API调用失败: {str(e)}")
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise Exception(f"聊天请求处理失败: {str(e)}")
    
    def _build_messages(self, request: ChatRequest, settings: ChatSettings) -> List[Dict[str, str]]:
        """
        构建发送给OpenAI的消息列表
        
        Args:
            request: 聊天请求
            settings: 聊天设置
            
        Returns:
            List[Dict[str, str]]: 格式化的消息列表
        """
        messages = []
        
        # 添加系统提示词（如果有）
        if settings.system_prompt:
            messages.append({
                "role": "system",
                "content": settings.system_prompt
            })
        
        # 添加对话历史
        if request.conversation_history:
            for msg in request.conversation_history[-10:]:  # 只保留最近10条历史消息
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        return messages
    
    async def create_streaming_completion(
        self, 
        request: ChatRequest,
        custom_settings: Optional[ChatSettings] = None
    ):
        """
        创建流式聊天完成请求（用于实时响应）
        
        Args:
            request: 聊天请求对象
            custom_settings: 自定义设置（可选）
            
        Yields:
            str: 流式响应的文本片段
        """
        try:
            # 使用自定义设置或默认设置
            settings_to_use = custom_settings or self.default_settings
            
            # 构建消息列表
            messages = self._build_messages(request, settings_to_use)
            
            # 获取模型参数
            model = request.model or settings_to_use.model
            temperature = request.temperature if request.temperature is not None else settings_to_use.temperature
            max_tokens = request.max_tokens or settings_to_use.max_tokens
            
            logger.info(f"Sending streaming chat completion request with model: {model}")
            
            # 调用OpenAI API（流式）
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except openai.APIError as e:
            logger.error(f"OpenAI API streaming error: {e}")
            raise Exception(f"OpenAI流式API调用失败: {str(e)}")
        except Exception as e:
            logger.error(f"Streaming completion error: {e}")
            raise Exception(f"流式聊天请求处理失败: {str(e)}")
    
    def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效
        
        Returns:
            bool: API密钥是否有效
        """
        try:
            # 发送一个简单的请求来验证API密钥
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except openai.AuthenticationError:
            logger.error("Invalid OpenAI API key")
            return False
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表
        
        Returns:
            List[str]: 可用模型列表
        """
        try:
            models = self.client.models.list()
            # 过滤出聊天模型
            chat_models = [
                model.id for model in models.data 
                if 'gpt' in model.id.lower() and 'chat' not in model.id.lower()
            ]
            return sorted(chat_models)
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return ["gpt-3.5-turbo", "gpt-4"]  # 返回默认模型列表


# 创建全局服务实例
chat_service = ChatService()
