from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Generator, Dict, Any
from app.repositories.conversation_repository import ConversationRepository, MessageRepository
from app.services.langgraph_service import LangGraphService
from app.core.models import Conversation, Message, DigitalHuman
from app.schemas.conversation import *
import json


class ConversationService:
    """对话服务层"""
    
    def __init__(self, db: Session, langgraph_service: LangGraphService):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        # 通过依赖注入获取 LangGraphService 实例
        self.langgraph_service = langgraph_service
    
    def create_conversation(
        self,
        conversation_data: ConversationCreate,
        user_id: int
    ) -> ConversationResponse:
        """创建新对话"""
        # 生成新的线程ID
        thread_id = self.langgraph_service.create_thread_id()
        
        # 创建对话
        conversation = self.conversation_repo.create_conversation(
            conversation_data, user_id, thread_id
        )
        
        return ConversationResponse.from_orm(conversation)
    
    def get_conversation_by_id(
        self,
        conversation_id: int,
        user_id: int
    ) -> Optional[ConversationResponse]:
        """获取对话详情"""
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        
        if not conversation:
            return None
        
        return ConversationResponse.from_orm(conversation)
    
    def get_conversations_paginated(
        self,
        page_request: ConversationPageRequest,
        user_id: int
    ) -> Tuple[List[ConversationResponse], int]:
        """分页获取对话列表"""
        conversations, total = self.conversation_repo.get_conversations_paginated(
            page_request, user_id
        )
        
        conversation_responses = [
            ConversationResponse.from_orm(conv) for conv in conversations
        ]
        
        return conversation_responses, total
    
    def update_conversation(
        self,
        conversation_id: int,
        conversation_data: ConversationUpdate,
        user_id: int
    ) -> Optional[ConversationResponse]:
        """更新对话"""
        conversation = self.conversation_repo.update_conversation(
            conversation_id, conversation_data, user_id
        )
        
        if not conversation:
            return None
        
        return ConversationResponse.from_orm(conversation)
    
    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话"""
        return self.conversation_repo.delete_conversation(conversation_id, user_id)
    
    def get_conversation_with_messages(
        self,
        conversation_id: int,
        user_id: int,
        message_limit: Optional[int] = None
    ) -> Optional[ConversationWithMessages]:
        """获取包含消息的对话"""
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        
        if not conversation:
            return None
        
        # 获取消息
        messages = self.message_repo.get_conversation_messages(
            conversation_id, message_limit
        )
        
        # 转换为响应模型
        conversation_response = ConversationResponse.from_orm(conversation)
        message_responses = [MessageResponse.from_orm(msg) for msg in messages]
        
        return ConversationWithMessages(
            **conversation_response.dict(),
            messages=message_responses
        )
    
    def send_message(
        self,
        conversation_id: int,
        message_content: str,
        user_id: int
    ) -> Optional[MessageResponse]:
        """发送消息（同步）"""
        # 验证对话
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            return None
        
        # 保存用户消息
        user_message = self.message_repo.create_message(
            conversation_id, "user", message_content
        )
        
        # 获取数字人配置
        digital_human_config = self._get_digital_human_config(
            conversation.digital_human_id
        )
        
        try:
            # 生成AI响应
            ai_response = self.langgraph_service.chat_sync(
                message_content,
                conversation.thread_id,
                digital_human_config
            )
            
            # 保存AI消息
            ai_message = self.message_repo.create_message(
                conversation_id, "assistant", ai_response
            )
            
            return MessageResponse.from_orm(ai_message)
            
        except ValueError as e:
            # LangGraph service errors (包括API密钥错误)
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(f"消息发送失败: {str(e)}")
    
    def send_message_stream(
        self,
        conversation_id: int,
        message_content: str,
        user_id: int
    ) -> Generator[str, None, None]:
        """发送消息（流式）"""
        # 验证对话
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            yield json.dumps({
                "type": "error",
                "content": "对话不存在或无权限访问"
            })
            return
        
        # 保存用户消息
        try:
            user_message = self.message_repo.create_message(
                conversation_id, "user", message_content
            )
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "content": f"保存消息失败: {str(e)}"
            })
            return

        # 发送用户消息确认
        yield json.dumps({
            "type": "message",
            "content": "",
            "metadata": {
                "message_id": user_message.id,
                "role": "user",
                "content": message_content
            }
        })

        # 获取数字人配置
        digital_human_config = self._get_digital_human_config(
            conversation.digital_human_id
        )

        # 流式生成AI响应
        full_response = ""
        try:
            for chunk in self.langgraph_service.chat_stream(
                message_content,
                conversation.thread_id,
                digital_human_config
            ):
                full_response += chunk
                yield json.dumps({
                    "type": "token",
                    "content": chunk
                })
        except ValueError as e:
            # LangGraph service errors (包括API密钥错误)
            yield json.dumps({
                "type": "error",
                "content": str(e)
            })
            return
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "content": f"AI响应生成失败: {str(e)}"
            })
            return

        # 保存AI消息
        try:
            ai_message = self.message_repo.create_message(
                conversation_id, "assistant", full_response
            )
        except Exception as e:
            # 即使保存失败，用户已经收到响应，记录警告即可
            print(f"Warning: Failed to save AI message: {str(e)}")
            ai_message = None

        # 发送完成消息
        yield json.dumps({
            "type": "done",
            "content": "",
            "metadata": {
                "message_id": ai_message.id if ai_message else None,
                "tokens_used": ai_message.tokens_used if ai_message else None
            }
        })
    
    def _get_digital_human_config(self, digital_human_id: int) -> Dict[str, Any]:
        """获取数字人配置"""
        digital_human = self.db.query(DigitalHuman).filter(
            DigitalHuman.id == digital_human_id
        ).first()
        
        if not digital_human:
            return {}
        
        return {
            "name": digital_human.name,
            "type": digital_human.type,
            "skills": digital_human.skills or [],
            "personality": digital_human.personality or {},
            "conversation_style": digital_human.conversation_style,
            "temperature": digital_human.temperature,
            "max_tokens": digital_human.max_tokens,
            "system_prompt": digital_human.system_prompt
        }
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        user_id: int,
        limit: Optional[int] = None
    ) -> List[MessageResponse]:
        """获取对话消息"""
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            return []
        
        messages = self.message_repo.get_conversation_messages(
            conversation_id, limit
        )
        
        return [MessageResponse.from_orm(msg) for msg in messages]
    
    def clear_conversation_history(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """清除对话历史"""
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            return False
        
        # 清除数据库中的消息
        success = self.message_repo.delete_conversation_messages(conversation_id)
        
        if success:
            # 清除LangChain中的对话历史
            self.langgraph_service.clear_conversation(conversation.thread_id)
        
        return success