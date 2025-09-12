import os
from typing import Generator, Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.core.messages import UserMessage, AssistantMessage, SystemMessage
from langgraph.graph import StateGraph, END
from app.core.checkpointer import MySQLCheckpointer
from app.core.database import get_db
from pydantic import BaseModel
import json
import uuid
import openai
from app.core.models import DigitalHuman


class ConversationState(BaseModel):
    """对话状态模型"""
    messages: List[BaseMessage] = []
    digital_human_config: Optional[Dict[str, Any]] = None
    thread_id: str = ""
    user_message: str = ""
    assistant_response: str = ""


class LangGraphService:
    """LangGraph集成服务"""
    
    def __init__(self, db_session_factory=None):
        try:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            # 验证 OpenAI API 密钥
            self._validate_openai_api_key()
            
            self.llm = ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-4o-mini",
                temperature=0.7,
                streaming=True,
                timeout=30
            )
            
            # 使用 MySQL 检查点保存器，支持版本管理和缓存
            self.checkpointer = MySQLCheckpointer(
                db_session_factory or get_db,
                cache_size=100,  # 缓存100个检查点
                cache_ttl=300    # 缓存5分钟
            )
            
            # 构建对话图
            self.graph = self._build_conversation_graph()
            
        except openai.AuthenticationError:
            raise ValueError("Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable.")
        except openai.RateLimitError:
            raise ValueError("OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise ValueError(f"OpenAI API error during initialization: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to initialize LangGraph service: {str(e)}")
    
    def _validate_openai_api_key(self):
        """验证 OpenAI API 密钥是否有效"""
        try:
            # 创建测试客户端
            test_client = ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-4o-mini",
                timeout=10
            )
            
            # 发送简单测试消息验证API密钥
            test_message = [UserMessage(content="test")]
            test_client.invoke(test_message)
            
        except openai.AuthenticationError:
            raise ValueError("Invalid OpenAI API key")
        except openai.RateLimitError:
            raise ValueError("OpenAI API rate limit exceeded")
        except openai.APIError as e:
            if "invalid_api_key" in str(e).lower():
                raise ValueError("Invalid OpenAI API key")
            raise ValueError(f"OpenAI API validation failed: {str(e)}")
        except Exception as e:
            # 网络错误或其他问题，我们允许服务继续初始化
            # 但会在实际使用时处理错误
            pass
    
    def _build_conversation_graph(self) -> StateGraph:
        """构建对话状态图"""
        workflow = StateGraph(ConversationState)
        
        # 添加节点
        workflow.add_node("process_input", self._process_user_input)
        workflow.add_node("generate_response", self._generate_ai_response)
        workflow.add_node("finalize", self._finalize_response)
        
        # 添加边
        workflow.set_entry_point("process_input")
        workflow.add_edge("process_input", "generate_response")
        workflow.add_edge("generate_response", "finalize")
        workflow.add_edge("finalize", END)
        
        # 编译图
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _process_user_input(self, state: ConversationState) -> ConversationState:
        """处理用户输入"""
        # 添加用户消息到历史
        user_msg = UserMessage(content=state.user_message)
        state.messages.append(user_msg)
        return state
    
    def _generate_ai_response(self, state: ConversationState) -> ConversationState:
        """生成AI响应"""
        # 获取数字人配置
        config = state.digital_human_config or {}
        
        # 构建系统提示
        system_prompt = self._build_system_prompt(config)
        
        # 准备消息列表
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # 添加历史消息（保留最近的对话）
        recent_messages = state.messages[-10:]  # 保留最近10条消息
        messages.extend(recent_messages)
        
        # 更新LLM配置
        self.llm.temperature = config.get("temperature", 0.7)
        self.llm.max_tokens = config.get("max_tokens", 2048)
        
        # 生成响应
        response = self.llm.invoke(messages)
        state.assistant_response = response.content
        
        return state
    
    def _finalize_response(self, state: ConversationState) -> ConversationState:
        """完成响应处理"""
        # 添加助手消息到历史
        ai_msg = AssistantMessage(content=state.assistant_response)
        state.messages.append(ai_msg)
        return state
    
    def _build_system_prompt(self, config: Dict[str, Any]) -> str:
        """构建系统提示词"""
        base_prompt = config.get("system_prompt", "")
        
        # 添加数字人特征
        personality_prompt = ""
        if "personality" in config:
            personality = config["personality"]
            personality_prompt = f"""
性格特征：
- 专业性: {personality.get('professionalism', 80)}/100
- 友善度: {personality.get('friendliness', 90)}/100  
- 幽默感: {personality.get('humor', 60)}/100
"""
        
        # 添加技能信息
        skills_prompt = ""
        if "skills" in config and config["skills"]:
            skills_prompt = f"专业技能: {', '.join(config['skills'])}"
        
        # 添加对话风格
        style_prompt = ""
        if "conversation_style" in config:
            style_prompt = f"对话风格: {config['conversation_style']}"
        
        # 组合完整提示词
        full_prompt = f"""
{base_prompt}

{personality_prompt}
{skills_prompt}
{style_prompt}

请根据以上配置与用户进行对话，保持一致的个性和专业水准。
"""
        
        return full_prompt.strip()
    
    def create_thread_id(self) -> str:
        """创建新的线程ID"""
        return str(uuid.uuid4())
    
    def chat_sync(
        self,
        message: str,
        thread_id: str,
        digital_human_config: Dict[str, Any]
    ) -> str:
        """同步聊天"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # 获取历史消息
            try:
                checkpoint = self.checkpointer.get(config["configurable"])
                if checkpoint and checkpoint.get("channel_values"):
                    existing_messages = checkpoint["channel_values"].get("messages", [])
                else:
                    existing_messages = []
            except:
                existing_messages = []
            
            initial_state = ConversationState(
                thread_id=thread_id,
                user_message=message,
                digital_human_config=digital_human_config,
                messages=existing_messages  # 包含历史消息
            )
            
            # 运行对话图
            result = self.graph.invoke(initial_state, config)
            
            return result.assistant_response
            
        except openai.AuthenticationError:
            raise ValueError("Invalid OpenAI API key. Please check your API configuration.")
        except openai.RateLimitError:
            raise ValueError("OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            if "invalid_api_key" in str(e).lower():
                raise ValueError("Invalid OpenAI API key")
            raise ValueError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Chat generation failed: {str(e)}")
    
    def chat_stream(
        self,
        message: str,
        thread_id: str,
        digital_human_config: Dict[str, Any]
    ) -> Generator[str, None, None]:
        """流式聊天"""
        try:
            # 获取数字人配置
            config_dict = {"configurable": {"thread_id": thread_id}}
            
            # 构建系统提示
            system_prompt = self._build_system_prompt(digital_human_config)
            
            # 从 PostgreSQL checkpointer 获取历史消息
            messages = []
            try:
                checkpoint = self.checkpointer.get(config_dict["configurable"])
                if checkpoint and checkpoint.get("channel_values"):
                    messages = checkpoint["channel_values"].get("messages", [])
            except:
                messages = []
            
            # 准备消息列表
            full_messages = []
            if system_prompt:
                full_messages.append(SystemMessage(content=system_prompt))
            
            # 添加历史消息（保留最近的对话）
            recent_messages = messages[-10:] if messages else []
            full_messages.extend(recent_messages)
            
            # 添加当前用户消息
            full_messages.append(UserMessage(content=message))
            
            # 更新LLM配置
            stream_llm = ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-4o-mini",
                temperature=digital_human_config.get("temperature", 0.7),
                max_tokens=digital_human_config.get("max_tokens", 2048),
                streaming=True
            )
            
            # 流式生成响应
            full_response = ""
            for chunk in stream_llm.stream(full_messages):
                if chunk.content:
                    full_response += chunk.content
                    yield chunk.content
            
            # PostgreSQL checkpointer 会自动从数据库读取历史
            # 消息已经通过 conversation_service 保存到数据库
            # 无需再手动缓存或保存状态
            
        except openai.AuthenticationError:
            yield json.dumps({
                "type": "error",
                "content": "Invalid OpenAI API key. Please check your API configuration."
            })
        except openai.RateLimitError:
            yield json.dumps({
                "type": "error", 
                "content": "OpenAI API rate limit exceeded. Please try again later."
            })
        except openai.APIError as e:
            if "invalid_api_key" in str(e).lower():
                yield json.dumps({
                    "type": "error",
                    "content": "Invalid OpenAI API key"
                })
            else:
                yield json.dumps({
                    "type": "error",
                    "content": f"OpenAI API error: {str(e)}"
                })
        except ConnectionError:
            yield json.dumps({
                "type": "error",
                "content": "Network connection failed. Please check your internet connection."
            })
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "content": f"Chat error: {str(e)}"
            })
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            # 首先尝试从内存缓存获取
            messages = []
            # 直接从 PostgreSQL checkpointer 获取
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = self.checkpointer.get(config["configurable"])
            
            if checkpoint and checkpoint.get("channel_values"):
                messages = checkpoint["channel_values"].get("messages", [])
            
            if not messages:
                return []
            
            history = []
            for msg in messages:
                if isinstance(msg, UserMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AssistantMessage):
                    history.append({"role": "assistant", "content": msg.content})
                elif isinstance(msg, SystemMessage):
                    history.append({"role": "system", "content": msg.content})
            
            return history
            
        except Exception:
            return []
    
    def clear_conversation(self, thread_id: str) -> bool:
        """清除对话历史"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            # 通过创建空状态来清除历史
            empty_state = ConversationState(
                thread_id=thread_id,
                messages=[],
                digital_human_config={}
            )
            # 使用图来保存空状态
            self.graph.invoke(empty_state, config)
            return True
        except Exception:
            return False