from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Generator, Dict, Any
from app.repositories.conversation_repository import ConversationRepository, MessageRepository
from app.services.langgraph_service import LangGraphService
from app.core.models import Conversation, Message, DigitalHuman
from app.schemas.conversation import *
import json


class ConversationService:
    
    def __init__(self, db: Session, langgraph_service: LangGraphService):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.langgraph_service = langgraph_service
    
    def create_conversation(
        self,
        conversation_data: ConversationCreate,
        user_id: int
    ) -> ConversationResponse:
        thread_id = self.langgraph_service.create_thread_id()
        
        conversation = self.conversation_repo.create_conversation(
            conversation_data, user_id, thread_id
        )
        
        return ConversationResponse.model_validate(conversation)
    
    def get_conversation_by_id(
        self,
        conversation_id: int,
        user_id: int
    ) -> Optional[ConversationResponse]:
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        
        if not conversation:
            return None
        
        return ConversationResponse.model_validate(conversation)
    
    def get_conversations_paginated(
        self,
        page_request: ConversationPageRequest,
        user_id: int
    ) -> Tuple[List[ConversationResponse], int]:
        conversations, total = self.conversation_repo.get_conversations_paginated(
            page_request, user_id
        )
        
        conversation_responses = [
            ConversationResponse.model_validate(conv) for conv in conversations
        ]
        
        return conversation_responses, total
    
    def update_conversation(
        self,
        conversation_id: int,
        conversation_data: ConversationUpdate,
        user_id: int
    ) -> Optional[ConversationResponse]:
        conversation = self.conversation_repo.update_conversation(
            conversation_id, conversation_data, user_id
        )
        
        if not conversation:
            return None
        
        return ConversationResponse.model_validate(conversation)
    
    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        return self.conversation_repo.delete_conversation(conversation_id, user_id)
    
    def get_conversation_with_messages(
        self,
        conversation_id: int,
        user_id: int,
        message_limit: Optional[int] = None
    ) -> Optional[ConversationWithMessages]:
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        
        if not conversation:
            return None
        
        messages = self.message_repo.get_conversation_messages(
            conversation_id, message_limit
        )
        
        conversation_response = ConversationResponse.model_validate(conversation)
        message_responses = [MessageResponse.model_validate(msg) for msg in messages]
        
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
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            return None
        
        user_message = self.message_repo.create_message(
            conversation_id, "user", message_content
        )
        
        digital_human_config = self._get_digital_human_config(
            conversation.digital_human_id
        )
        
        try:
            ai_response = self.langgraph_service.chat_sync(
                message_content,
                conversation.thread_id,
                digital_human_config
            )
            
            ai_message = self.message_repo.create_message(
                conversation_id, "assistant", ai_response
            )
            
            return MessageResponse.model_validate(ai_message)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(f"消息发送失败: {str(e)}")
    
    def send_message_stream(
        self,
        conversation_id: int,
        message_content: str,
        user_id: int
    ) -> Generator[str, None, None]:
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            yield json.dumps({
                "type": "error",
                "content": "对话不存在或无权限访问"
            })
            return
        
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

        yield json.dumps({
            "type": "message",
            "content": "",
            "metadata": {
                "message_id": user_message.id,
                "role": "user",
                "content": message_content
            }
        })

        digital_human_config = self._get_digital_human_config(
            conversation.digital_human_id
        )

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

        try:
            ai_message = self.message_repo.create_message(
                conversation_id, "assistant", full_response
            )
        except Exception as e:
            print(f"Warning: Failed to save AI message: {str(e)}")
            ai_message = None

        yield json.dumps({
            "type": "done",
            "content": "",
            "metadata": {
                "message_id": ai_message.id if ai_message else None,
                "tokens_used": ai_message.tokens_used if ai_message else None
            }
        })
    
    def _get_digital_human_config(self, digital_human_id: int) -> Dict[str, Any]:
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
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            return []
        
        messages = self.message_repo.get_conversation_messages(
            conversation_id, limit
        )
        
        return [MessageResponse.model_validate(msg) for msg in messages]
    
    def clear_conversation_history(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        conversation = self.conversation_repo.get_conversation_by_id(
            conversation_id, user_id
        )
        if not conversation:
            return False
        
        success = self.message_repo.delete_conversation_messages(conversation_id)
        
        if success:
            self.langgraph_service.clear_conversation(conversation.thread_id)
        
        return success