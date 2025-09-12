from typing import Literal, Dict, Any, Optional
from langchain_core.messages import HumanMessage as BaseHumanMessage
from langchain_core.messages import AIMessage as BaseAIMessage
from langchain_core.messages import SystemMessage as BaseSystemMessage
from langchain_core.messages import BaseMessage


class UserMessage(BaseHumanMessage):
    """标准用户消息类，使用 'user' 作为类型标识"""
    type: Literal["user"] = "user"


class AssistantMessage(BaseAIMessage):
    """标准助手消息类，使用 'assistant' 作为类型标识"""
    type: Literal["assistant"] = "assistant"


class SystemMessage(BaseSystemMessage):
    """系统消息类，保持 'system' 类型标识"""
    type: Literal["system"] = "system"


def is_message_dict(obj: Any) -> bool:
    """判断对象是否为消息字典格式"""
    if not isinstance(obj, dict):
        return False
    
    # 必须有 role 或 type 字段，以及 content 字段
    has_role = "role" in obj or "type" in obj
    has_content = "content" in obj
    
    if not (has_role and has_content):
        return False
    
    # 只允许这些键
    allowed_keys = {"role", "type", "content", "additional_kwargs"}
    return set(obj.keys()).issubset(allowed_keys)


def deserialize_message(message_dict: Dict[str, Any]) -> Optional[BaseMessage]:
    """根据 role 字段反序列化消息，无效格式返回 None"""
    if not is_message_dict(message_dict):
        return None
        
    role = message_dict.get("role") or message_dict.get("type")
    content = message_dict.get("content", "")
    kwargs = message_dict.get("additional_kwargs", {})
    
    if role == "user":
        return UserMessage(content=content, **kwargs)
    elif role == "assistant":
        return AssistantMessage(content=content, **kwargs)
    elif role == "system":
        return SystemMessage(content=content, **kwargs)
    else:
        return None  # 未知角色返回 None


def serialize_message(msg) -> Dict[str, Any]:
    """将消息序列化为标准格式"""
    return {
        "role": msg.type,
        "content": msg.content,
        "additional_kwargs": getattr(msg, 'additional_kwargs', {})
    }