import os
from typing import Generator, Dict, Any, Optional, List
from datetime import datetime
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
from app.services.hybrid_search_service import HybridSearchService
from app.core.logger import logger


class ConversationState(BaseModel):
    """对话状态模型"""
    messages: List[BaseMessage] = []
    digital_human_config: Optional[Dict[str, Any]] = None
    thread_id: str = ""
    user_message: str = ""
    assistant_response: str = ""
    memory_context: str = ""  # 格式化的记忆文本（用于AI上下文）
    memory_search_results: Optional[Dict[str, Any]] = None  # 原始搜索结果（用于保存）


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

            # 初始化混合搜索服务
            self.hybrid_search_service = HybridSearchService()

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
        workflow.add_node("search_memory", self._search_memory)  # 新增：记忆搜索节点
        workflow.add_node("generate_response", self._generate_ai_response)
        workflow.add_node("finalize", self._finalize_response)

        # 添加边
        workflow.set_entry_point("process_input")
        workflow.add_edge("process_input", "search_memory")  # 先搜索记忆
        workflow.add_edge("search_memory", "generate_response")  # 再生成响应
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

    def _search_memory(self, state: ConversationState) -> ConversationState:
        """搜索相关记忆"""
        try:
            # 获取数字人ID
            digital_human_id = state.digital_human_config.get("id") if state.digital_human_config else None
            if not digital_human_id:
                logger.debug("No digital_human_id found, skipping memory search")
                return state

            logger.info(f"Searching memories for digital_human_id: {digital_human_id}, query: {state.user_message[:50]}...")

            # 使用同步方式搜索记忆
            import asyncio
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 在事件循环中运行异步搜索
            search_results = loop.run_until_complete(
                self.hybrid_search_service.search(
                    query=state.user_message,
                    digital_human_id=digital_human_id,
                    mode="hybrid",
                    entity_limit=10,
                    relationship_limit=5,
                    expand_graph=True
                )
            )

            # 保存原始搜索结果
            state.memory_search_results = search_results

            # 格式化记忆为文本（用于AI上下文）
            state.memory_context = self._format_memory_context(search_results)

            if state.memory_context:
                logger.info(f"Found {len(search_results.get('entities', []))} entities and {len(search_results.get('relationships', []))} relationships")
            else:
                logger.debug("No relevant memories found")

            return state

        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            # 记忆搜索失败不影响对话，继续流程
            return state

    def _format_memory_context(self, search_results: Dict[str, Any]) -> str:
        """将搜索结果格式化为简洁的上下文文本"""
        context_parts = []

        # 格式化实体（取前5个最相关的）
        entities = search_results.get("entities", [])
        if entities:
            entity_texts = []
            for e in entities[:5]:
                name = e.get('name', '')
                description = e.get('description', '')
                if name:
                    if description:
                        entity_texts.append(f"- {name}: {description}")
                    else:
                        entity_texts.append(f"- {name}")

            if entity_texts:
                context_parts.append("相关记忆：\n" + "\n".join(entity_texts))

        # 格式化关系（取前3个最相关的）
        relationships = search_results.get("relationships", [])
        if relationships:
            rel_texts = []
            for r in relationships[:3]:
                source = r.get('source', '')
                target = r.get('target', '')
                description = r.get('description', '')
                types = r.get('types', '')

                if source and target:
                    if description:
                        rel_texts.append(f"- {source} → {target}: {description}")
                    elif types:
                        rel_texts.append(f"- {source} → {target} ({types})")
                    else:
                        rel_texts.append(f"- {source} → {target}")

            if rel_texts:
                context_parts.append("相关关系：\n" + "\n".join(rel_texts))

        return "\n\n".join(context_parts) if context_parts else ""
    
    def _generate_ai_response(self, state: ConversationState) -> ConversationState:
        """生成AI响应"""
        # 获取数字人配置，确保是字典类型
        config = state.digital_human_config
        if not isinstance(config, dict):
            logger.warning(f"digital_human_config is not a dict: {type(config)}, using default config")
            config = {}
        if not config:
            config = {}

        # 构建系统提示（包含记忆上下文）
        system_prompt = self._build_system_prompt(config)
        if state.memory_context:
            system_prompt += f"\n\n基于以下相关记忆回答用户：\n{state.memory_context}"

        # 准备消息列表
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 添加历史消息（保留最近的对话）
        recent_messages = state.messages[-10:]  # 保留最近10条消息
        messages.extend(recent_messages)

        # 安全获取配置值并更新LLM配置
        self.llm.temperature = config.get("temperature", 0.7) if isinstance(config, dict) else 0.7
        self.llm.max_tokens = config.get("max_tokens", 2048) if isinstance(config, dict) else 2048

        # 生成响应
        response = self.llm.invoke(messages)
        state.assistant_response = response.content

        return state

    def _generate_ai_response_stream(self, state: ConversationState) -> Generator[str, None, None]:
        """流式生成AI响应"""
        # 获取数字人配置，确保是字典类型
        config = state.digital_human_config
        if not isinstance(config, dict):
            logger.warning(f"digital_human_config is not a dict: {type(config)}, using default config")
            config = {}
        if not config:
            config = {}

        # 构建系统提示（包含记忆上下文）
        system_prompt = self._build_system_prompt(config)
        if state.memory_context:
            system_prompt += f"\n\n基于以下相关记忆回答用户：\n{state.memory_context}"

        # 准备消息列表
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 添加历史消息（保留最近的对话）
        recent_messages = state.messages[-10:]  # 保留最近10条消息
        messages.extend(recent_messages)

        # 安全获取配置值
        temperature = config.get("temperature", 0.7) if isinstance(config, dict) else 0.7
        max_tokens = config.get("max_tokens", 2048) if isinstance(config, dict) else 2048

        # 创建流式LLM
        stream_llm = ChatOpenAI(
            api_key=self.openai_api_key,
            model="gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True
        )

        # 流式生成响应
        full_response = ""
        for chunk in stream_llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        # 保存完整响应到状态
        state.assistant_response = full_response
    
    def _finalize_response(self, state: ConversationState) -> ConversationState:
        """完成响应处理"""
        # 添加助手消息到历史
        ai_msg = AssistantMessage(content=state.assistant_response)
        state.messages.append(ai_msg)
        return state
    
    def _build_system_prompt(self, config: Dict[str, Any]) -> str:
        """构建系统提示词"""
        # 确保config是字典类型
        if not isinstance(config, dict):
            logger.warning(f"[PROMPT DEBUG] config is not a dict: {type(config)}, using empty config")
            config = {}

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
    
    def chat_stream(
        self,
        message: str,
        thread_id: str,
        digital_human_config: Dict[str, Any]
    ) -> Generator[str, None, None]:
        """流式聊天 - 使用图工作流但流式生成响应"""
        try:
            config = {"configurable": {"thread_id": thread_id}}

            # 获取历史消息
            existing_messages = []
            try:
                checkpoint = self.checkpointer.get(config["configurable"])
                # 添加类型检查以确保 checkpoint 和 channel_values 都是字典
                if checkpoint and isinstance(checkpoint, dict):
                    channel_values = checkpoint.get("channel_values", {})
                    if isinstance(channel_values, dict):
                        existing_messages = channel_values.get("messages", [])
                    else:
                        logger.warning(f"Invalid channel_values type for thread {thread_id}: {type(channel_values)}")
                        existing_messages = []
            except Exception as e:
                logger.warning(f"Failed to get checkpoint for thread {thread_id}: {e}")
                existing_messages = []

            # 创建初始状态
            initial_state = ConversationState(
                thread_id=thread_id,
                user_message=message,
                digital_human_config=digital_human_config,
                messages=existing_messages
            )

            # 创建一个特殊的流式图用于流式响应
            # 注意：这里需要特殊处理，因为标准的 graph.invoke 不支持流式响应

            # 1. 先执行非流式节点（处理输入和搜索记忆）
            state = self._process_user_input(initial_state)
            state = self._search_memory(state)

            # 保存中间状态到 checkpointer
            intermediate_checkpoint = {
                "v": 1,
                "ts": datetime.now().isoformat(),
                "channel_values": {
                    "messages": state.messages,
                    "memory_context": state.memory_context,
                    "memory_search_results": state.memory_search_results
                },
                "channel_versions": {
                    "messages": len(state.messages)
                },
                "versions_seen": {}
            }
            self.checkpointer.put(
                config,
                intermediate_checkpoint,
                {"source": "stream_intermediate", "node": "search_memory"},
                {}
            )

            # 如果有记忆搜索结果，返回详细信息
            if state.memory_search_results and isinstance(state.memory_search_results, dict):
                # 获取实体和关系
                entities = state.memory_search_results.get("entities", [])
                relationships = state.memory_search_results.get("relationships", [])

                # 简化实体数据（只保留前5个最相关的）
                simplified_entities = []
                for e in entities[:5]:
                    # 确保e是字典类型
                    if isinstance(e, dict):
                        simplified_entities.append({
                            "name": e.get("name", ""),
                            "types": e.get("types", ""),
                            "description": e.get("description", ""),
                            "confidence": float(e.get("confidence", 0))
                        })

                # 简化关系数据（只保留前3个最相关的）
                simplified_relationships = []
                for r in relationships[:3]:
                    # 确保r是字典类型
                    if isinstance(r, dict):
                        simplified_relationships.append({
                            "source": r.get("source", ""),
                            "target": r.get("target", ""),
                            "types": r.get("types", ""),
                            "description": r.get("description", "")
                        })

                yield json.dumps({
                    "type": "memory",
                    "content": f"找到 {len(entities)} 个实体和 {len(relationships)} 个关系",
                    "metadata": {
                        "has_memory": True,
                        "entity_count": len(entities),
                        "relationship_count": len(relationships),
                        "entities": simplified_entities,
                        "relationships": simplified_relationships
                    }
                }, ensure_ascii=False)

            # 2. 流式生成响应
            for chunk in self._generate_ai_response_stream(state):
                yield chunk

            # 3. 完成响应处理
            state = self._finalize_response(state)

            # 4. 保存最终状态到 checkpointer

            final_checkpoint = {
                "v": 1,
                "ts": datetime.now().isoformat(),
                "channel_values": {
                    "messages": state.messages,
                    "memory_context": state.memory_context,
                    "memory_search_results": state.memory_search_results,
                    "assistant_response": state.assistant_response
                },
                "channel_versions": {
                    "messages": len(state.messages)
                },
                "versions_seen": {}
            }

            self.checkpointer.put(
                config,
                final_checkpoint,
                {"source": "stream_final", "node": "finalize"},
                {}
            )
            
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

            # 添加类型检查以确保 checkpoint 和 channel_values 都是字典
            if checkpoint and isinstance(checkpoint, dict):
                channel_values = checkpoint.get("channel_values", {})
                if isinstance(channel_values, dict):
                    messages = channel_values.get("messages", [])
                else:
                    logger.warning(f"Invalid channel_values type for thread {thread_id}: {type(channel_values)}")
                    messages = []
            
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