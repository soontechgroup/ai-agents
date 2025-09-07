from typing import Dict, List, Any, Generator, Optional, AsyncGenerator, TypedDict, Annotated
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import operator

from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.graph_service import GraphService
from app.repositories.training_message_repository import TrainingMessageRepository
from app.core.logger import logger
from app.core.config import settings


class TrainingState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    digital_human_id: int
    user_id: int
    current_message: str
    extracted_knowledge: Dict[str, Any]
    knowledge_context: Dict[str, Any]
    next_question: str
    should_extract: bool
    should_explore_deeper: bool
    conversation_stage: str
    total_knowledge_points: int
    categories: Dict[str, Any]
    current_step: str
    completed_steps: Annotated[List[str], operator.add]
    step_results: Dict[str, Any]
    thinking_process: Annotated[List[str], operator.add]
    events: Annotated[List[Dict[str, Any]], operator.add]  # 事件队列，用于流式通知


class DigitalHumanTrainingService:
    
    def __init__(
        self,
        training_message_repo: TrainingMessageRepository,
        knowledge_extractor: KnowledgeExtractor,
        graph_service: GraphService
    ):
        self.training_message_repo = training_message_repo
        self.knowledge_extractor = knowledge_extractor
        self.graph_service = graph_service
        
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.3
        )
        
        self.training_graph = self._build_training_graph()
    
    def _build_training_graph(self):
        workflow = StateGraph(TrainingState)
        
        workflow.add_node("intent_recognition", self._recognize_intent)
        workflow.add_node("knowledge_extraction", self._extract_knowledge)
        workflow.add_node("context_analysis", self._analyze_context)
        workflow.add_node("question_generation", self._generate_question)
        workflow.add_node("save_message", self._save_message)
        
        workflow.set_entry_point("intent_recognition")
        
        workflow.add_conditional_edges(
            "intent_recognition",
            self._route_after_intent,
            {
                "extract": "knowledge_extraction",
                "analyze": "context_analysis",
                "direct": "question_generation"
            }
        )
        
        workflow.add_edge("knowledge_extraction", "context_analysis")
        workflow.add_edge("context_analysis", "question_generation")
        workflow.add_edge("question_generation", "save_message")
        workflow.add_edge("save_message", END)
        
        return workflow.compile()
    
    def _create_event(
        self, 
        event_type: str, 
        node: str, 
        message: str, 
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        event = {
            "type": event_type,
            "node": node,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if result is not None:
            event["result"] = result
        return event
    
    def save_graph_visualization(self, output_dir: str = "graph_visualizations"):
        """保存工作流图的可视化"""
        from pathlib import Path
        
        Path(output_dir).mkdir(exist_ok=True)
        graph = self.training_graph.get_graph()
        
        # 1. 尝试生成 PNG 图片
        png_path = f"{output_dir}/training_graph.png"
        try:
            graph.draw_png(output_file_path=png_path)
            logger.info(f"✅ 图已保存为 PNG: {png_path}")
            return png_path
        except Exception:
            logger.debug("PNG 生成失败，尝试 Mermaid 格式")
        
        # 2. 备选方案：保存 Mermaid
        try:
            mermaid_path = f"{output_dir}/training_graph.mmd"
            Path(mermaid_path).write_text(graph.draw_mermaid())
            logger.info(f"✅ 图已保存为 Mermaid: {mermaid_path}")
            logger.info("📊 可在 https://mermaid.live 查看")
            return mermaid_path
        except Exception as e:
            logger.error(f"❌ 无法生成任何可视化: {e}")
            return None
    
    def _recognize_intent(self, state: TrainingState) -> Dict[str, Any]:
        """
        识别用户意图并判断对话阶段。
        
        分析用户消息内容，识别其意图类型（如信息分享、提问、打招呼等），
        并判断当前对话所处的阶段（初始、探索、深化、总结）。
        
        Args:
            state: 当前训练状态，必须包含 current_message 字段
            
        Returns:
            更新后的状态字典，包含：
            - intent: 识别出的意图类型
            - should_extract: 是否需要进行知识抽取
            - conversation_stage: 当前对话阶段
            - step_results: 包含意图识别结果
            - events: 节点执行事件列表
        """
        # 节点开始事件
        events = [self._create_event(
            "node_start",
            "intent_recognition",
            "🔍 开始识别用户意图..."
        )]
        
        current_step = "recognizing_intent"
        thinking_process = ["正在识别用户意图..."]
        
        # 添加思考步骤
        events.append(self._create_event(
            "thinking",
            "intent_recognition",
            "💭 分析消息内容，识别用户意图..."
        ))
        
        prompt = f"""
分析以下用户消息的意图和内容类型：

用户消息: {state['current_message']}

请判断：
1. 意图类型（information_sharing/question_asking/clarification/greeting/other）
2. 当前对话阶段（initial/exploring/deepening/concluding）

返回JSON格式：
{{
    "intent": "...",
    "stage": "..."
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"意图识别响应解析失败: {e}")
            logger.error(f"原始响应: {response.content}")
            raise ValueError(f"意图识别响应格式错误: {str(e)}")
        
        intent = result.get("intent", "other")
        conversation_stage = result.get("stage", "exploring")
        
        # 基于意图设置是否需要提取知识
        should_extract = False
        if intent == "information_sharing":
            should_extract = True
        elif intent == "greeting":
            should_extract = False
        elif intent == "question_asking":
            # 问题可能包含知识，也可能不包含
            # 这里简单处理，如果是探索阶段的问题，可能有知识
            should_extract = conversation_stage in ["exploring", "deepening"]
        elif intent == "other":
            # 对于 other 类型，基于文本长度和内容密度判断
            # 长文本（超过100字符）或包含专业术语的文本应该提取
            text_length = len(state['current_message'])
            if text_length > 100:
                should_extract = True
                logger.debug(f"长文本({text_length}字符)被识别为需要提取知识")
            else:
                should_extract = False
        else:
            should_extract = False
        
        # 意图存储在 step_results 中，不污染顶级 state
        step_results = state.get('step_results', {}).copy()
        step_results["intent_recognition"] = {
            "intent": intent,
            "should_extract": should_extract,
            "stage": conversation_stage
        }
        
        # 节点完成事件
        events.append(self._create_event(
            "node_complete",
            "intent_recognition",
            f"✅ 意图识别完成: {intent}",
            {
                "intent": intent,
                "stage": conversation_stage,
                "should_extract": should_extract
            }
        ))
        
        completed_steps = ["intent_recognition"]
        thinking_process.append(f"识别到意图: {intent}, 对话阶段: {conversation_stage}")
        
        # 返回更新的字段
        return {
            "current_step": current_step,
            "conversation_stage": conversation_stage,
            "should_extract": should_extract,
            "step_results": step_results,
            "completed_steps": completed_steps,
            "thinking_process": thinking_process,
            "events": events
        }
    
    def _route_after_intent(self, state: TrainingState) -> str:
        if state.get('should_extract', False):
            return "extract"
        elif state.get('total_knowledge_points', 0) > 5:
            return "analyze"
        else:
            return "direct"
    
    async def _extract_knowledge(self, state: TrainingState) -> Dict[str, Any]:
        """
        从用户消息中提取知识实体和关系。
        
        使用知识抽取器分析文本，识别实体（人物、组织、技能等）
        及其之间的关系，并将结果存储到图数据库中。
        
        Args:
            state: 当前训练状态，必须包含 current_message 和 digital_human_id
            
        Returns:
            更新后的状态字典，包含：
            - extracted_knowledge: 提取的实体和关系
            - step_results: 包含知识抽取结果统计
            - events: 节点执行事件列表
        """
        events = [self._create_event(
            "node_start",
            "knowledge_extraction",
            "🧠 开始提取知识点..."
        )]
        
        current_step = "extracting_knowledge"
        thinking_process = ["正在提取知识点..."]
        
        if not state.get('should_extract', False):
            extracted_knowledge = {"entities": [], "relationships": []}
            completed_steps = ["knowledge_extraction"]
            
            events.append(self._create_event(
                "node_complete",
                "knowledge_extraction",
                "ℹ️ 无需提取知识"
            ))
            
            return {
                "current_step": current_step,
                "extracted_knowledge": extracted_knowledge,
                "completed_steps": completed_steps,
                "thinking_process": thinking_process,
                "events": events
            }
        
        extraction_result = await self.knowledge_extractor.extract(state['current_message'])
        extracted_knowledge = extraction_result
        
        entity_count = len(extraction_result.get("entities", []))
        relationship_count = len(extraction_result.get("relationships", []))
        
        for entity in extraction_result.get("entities", []):
            await self.graph_service.store_digital_human_entity(state['digital_human_id'], entity)
        
        for relationship in extraction_result.get("relationships", []):
            await self.graph_service.store_digital_human_relationship(state['digital_human_id'], relationship)
        
        step_results = state.get('step_results', {}).copy()
        step_results["knowledge_extraction"] = {
            "entities_count": entity_count,
            "relationships_count": relationship_count,
            "extracted": extraction_result
        }
        
        events.append(self._create_event(
            "node_complete",
            "knowledge_extraction",
            f"✅ 知识提取完成: {entity_count} 个实体, {relationship_count} 个关系",
            {
                "entities_count": entity_count,
                "relationships_count": relationship_count
            }
        ))
        
        completed_steps = ["knowledge_extraction"]
        thinking_process.append(f"提取到 {entity_count} 个实体, {relationship_count} 个关系")
        
        return {
            "current_step": current_step,
            "extracted_knowledge": extracted_knowledge,
            "step_results": step_results,
            "completed_steps": completed_steps,
            "thinking_process": thinking_process,
            "events": events
        }
    
    def _analyze_context(self, state: TrainingState) -> Dict[str, Any]:
        """
        分析数字人已有的知识上下文。
        
        从图数据库获取数字人已存储的知识点，分析其分布情况，
        判断是否需要深入探索某些领域。
        
        Args:
            state: 当前训练状态，必须包含 digital_human_id
            
        Returns:
            更新后的状态字典，包含：
            - knowledge_context: 知识上下文信息
            - total_knowledge_points: 总知识点数
            - categories: 知识分类统计
            - should_explore_deeper: 是否需要深入探索
            - events: 节点执行事件列表
        """
        events = [self._create_event(
            "node_start",
            "context_analysis",
            "🔎 开始分析知识图谱上下文..."
        )]
        
        current_step = "analyzing_context"
        thinking_process = ["正在分析知识图谱上下文..."]
        
        context = self._get_current_context(state['digital_human_id'])
        knowledge_context = context
        total_knowledge_points = context.get("total_knowledge_points", 0)
        categories = context.get("categories", {})
        
        should_explore_deeper = False
        if total_knowledge_points > 20 and not categories.get("hobby"):
            should_explore_deeper = True
        elif total_knowledge_points > 10 and len(categories) < 3:
            should_explore_deeper = True
        
        step_results = state.get('step_results', {}).copy()
        step_results["context_analysis"] = {
            "total_points": total_knowledge_points,
            "categories_count": len(categories),
            "should_explore_deeper": should_explore_deeper
        }
        
        events.append(self._create_event(
            "node_complete",
            "context_analysis",
            f"✅ 上下文分析完成: {total_knowledge_points} 个知识点",
            {
                "total_points": total_knowledge_points,
                "categories_count": len(categories)
            }
        ))
        
        completed_steps = ["context_analysis"]
        thinking_process.append(f"已了解 {total_knowledge_points} 个知识点，涵盖 {len(categories)} 个领域")
        
        return {
            "current_step": current_step,
            "knowledge_context": knowledge_context,
            "total_knowledge_points": total_knowledge_points,
            "categories": categories,
            "should_explore_deeper": should_explore_deeper,
            "step_results": step_results,
            "completed_steps": completed_steps,
            "thinking_process": thinking_process,
            "events": events
        }
    
    def _generate_question(self, state: TrainingState) -> Dict[str, Any]:
        """
        基于当前状态生成引导性问题。
        
        根据用户的回答、已提取的知识和对话阶段，
        生成下一个自然的引导性问题，推动对话深入。
        
        Args:
            state: 当前训练状态，包含对话历史和知识上下文
            
        Returns:
            更新后的状态字典，包含：
            - next_question: 生成的引导性问题
            - step_results: 包含问题生成相关信息
            - events: 节点执行事件列表
        """
        events = [self._create_event(
            "node_start",
            "question_generation",
            "❓ 开始生成引导性问题..."
        )]
        
        current_step = "generating_question"
        thinking_process = ["正在生成引导性问题..."]
        
        context_prompt = self._build_context_prompt(state)
        
        prompt = f"""
你是一个正在了解用户的数字人。基于当前对话状态，生成下一个引导性问题。

{context_prompt}

要求：
1. 问题要自然、友好
2. 根据用户刚才的回答延伸
3. 逐步深入了解用户
4. 不要重复已经问过的内容

生成一个引导性问题：
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        next_question = response.content.strip()
        
        step_results = state.get('step_results', {}).copy()
        step_results["question_generation"] = {
            "question": next_question,
            "based_on_stage": state.get('conversation_stage', 'exploring')
        }
        
        events.append(self._create_event(
            "node_complete",
            "question_generation",
            "✅ 问题生成完成",
            {
                "question": next_question[:50] + "..." if len(next_question) > 50 else next_question
            }
        ))
        
        completed_steps = ["question_generation"]
        thinking_process.append("已生成引导性问题")
        
        return {
            "current_step": current_step,
            "next_question": next_question,
            "step_results": step_results,
            "completed_steps": completed_steps,
            "thinking_process": thinking_process,
            "events": events
        }
    
    def _build_context_prompt(self, state: Dict[str, Any]) -> str:
        prompt_parts = []
        
        if state.get('current_message'):
            prompt_parts.append(f"用户刚才说: {state['current_message']}")
        
        extracted_knowledge = state.get('extracted_knowledge', {})
        if extracted_knowledge and extracted_knowledge.get("entities"):
            entities = extracted_knowledge["entities"]
            entity_names = [e.get("name") for e in entities[:3]]
            prompt_parts.append(f"提取到的实体: {', '.join(entity_names)}")
        
        total_knowledge_points = state.get('total_knowledge_points', 0)
        if total_knowledge_points > 0:
            prompt_parts.append(f"已了解的知识点数: {total_knowledge_points}")
        
        categories = state.get('categories', {})
        if categories:
            cat_summary = []
            for cat, info in categories.items():
                if isinstance(info, dict) and info.get("count"):
                    cat_summary.append(f"{cat}({info['count']}个)")
            if cat_summary:
                prompt_parts.append(f"已了解的领域: {', '.join(cat_summary)}")
        
        conversation_stage = state.get('conversation_stage', 'exploring')
        prompt_parts.append(f"当前对话阶段: {conversation_stage}")
        
        return "\n".join(prompt_parts)
    
    async def _save_message(self, state: TrainingState) -> Dict[str, Any]:
        """
        保存消息到数据库。
        
        将用户消息和助手回复持久化到数据库中，
        用于后续的对话历史查询和分析。
        
        Args:
            state: 当前训练状态，必须包含 digital_human_id, user_id 和 current_message
            
        Returns:
            更新后的状态字典，包含：
            - messages: 更新后的消息列表（追加新消息）
            - step_results: 包含消息保存结果
            - events: 节点执行事件列表
        """
        events = [self._create_event(
            "node_start",
            "save_message",
            "💾 开始保存对话记录..."
        )]
        
        current_step = "saving_message"
        thinking_process = ["正在保存对话记录..."]
        
        message_data = {
            "digital_human_id": state['digital_human_id'],
            "user_id": state['user_id'],
            "content": state['current_message'],
            "extracted_knowledge": state.get('extracted_knowledge', {}),
            "conversation_stage": state.get('conversation_stage', 'exploring'),
            "next_question": state.get('next_question', '')
        }
        
        step_results = state.get('step_results', {}).copy()
        step_results["message_saving"] = {
            "saved": True,
            "message_length": len(state['current_message'])
        }
        
        events.append(self._create_event(
            "node_complete",
            "save_message",
            "✅ 对话记录保存完成"
        ))
        
        completed_steps = ["save_message"]
        thinking_process.append("对话记录已保存")
        
        return {
            "current_step": current_step,
            "step_results": step_results,
            "completed_steps": completed_steps,
            "thinking_process": thinking_process,
            "events": events
        }
    
    def _get_current_context(self, digital_human_id: int) -> Dict[str, Any]:
        try:
            return self.graph_service.get_digital_human_knowledge_context(digital_human_id)
        except Exception as e:
            logger.error(f"获取训练上下文失败: {str(e)}")
            return {"total_knowledge_points": 0, "categories": {}, "recent_entities": []}
    
    async def _save_and_send_assistant_message(
        self,
        digital_human_id: int,
        user_id: int,
        question: str
    ) -> AsyncGenerator[str, None]:
        """保存助手消息并发送事件"""
        assistant_msg = self.training_message_repo.create_training_message(
            digital_human_id=digital_human_id,
            user_id=user_id,
            role="assistant",
            content=question
        )
        
        yield json.dumps({
            "type": "assistant_question",
            "id": assistant_msg.id,
            "data": question
        }, ensure_ascii=False)
    
    def _extract_next_question(self, result) -> Optional[str]:
        """从结果中提取下一个问题"""
        if not result:
            return None
            
        # 尝试作为字典访问
        if hasattr(result, '__getitem__') and 'next_question' in result:
            return result['next_question']
        # 尝试作为对象属性访问
        elif hasattr(result, 'next_question'):
            return result.next_question
            
        return None
    
    async def process_training_conversation(
        self,
        digital_human_id: int,
        user_message: str,
        user_id: int
    ) -> Generator[str, None, None]:
        user_msg = None
        state = None
        
        try:
            user_msg = self.training_message_repo.create_training_message(
                digital_human_id=digital_human_id,
                user_id=user_id,
                role="user",
                content=user_message
            )
            
            yield json.dumps({
                "type": "user_message",
                "id": user_msg.id,
                "data": user_message
            }, ensure_ascii=False)
            
            state = TrainingState(
                digital_human_id=digital_human_id,
                user_id=user_id,
                current_message=user_message,
                messages=[HumanMessage(content=user_message)]
            )
            
            yield json.dumps({
                "type": "thinking",
                "data": "开始分析对话..."
            }, ensure_ascii=False)
            
            # 保存最终状态
            final_state = None
            previous_state = None
            
            # 使用 astream 获取状态更新
            async for chunk in self.training_graph.astream(state):
                # chunk 是 {"节点名": 节点状态} 格式
                if chunk and isinstance(chunk, dict):
                    logger.debug(f"📊 状态更新: {list(chunk.keys())}")
                    
                    # 处理每个节点的输出
                    for node_name, node_state in chunk.items():
                        # 跳过内部节点
                        if node_name.startswith('__'):
                            continue
                            
                        # 节点状态可能是 dict 或对象
                        if isinstance(node_state, dict):
                            # 从 dict 中提取字段
                            events = node_state.get('events', [])
                            completed_steps = node_state.get('completed_steps', [])
                            thinking_process = node_state.get('thinking_process', [])
                            extracted_knowledge = node_state.get('extracted_knowledge', {})
                            next_question = node_state.get('next_question', '')
                            conversation_stage = node_state.get('conversation_stage', '')
                        else:
                            # 从对象中提取字段
                            events = getattr(node_state, 'events', [])
                            completed_steps = getattr(node_state, 'completed_steps', [])
                            thinking_process = getattr(node_state, 'thinking_process', [])
                            extracted_knowledge = getattr(node_state, 'extracted_knowledge', {})
                            next_question = getattr(node_state, 'next_question', '')
                            conversation_stage = getattr(node_state, 'conversation_stage', '')
                            
                        # 发送节点事件
                        if events:
                            for event in events:
                                # 发送节点内部的事件
                                logger.debug(f"📨 发送事件: {event.get('type')} - {event.get('node')}")
                                yield json.dumps(event, ensure_ascii=False)
                        
                        # 检测新完成的步骤
                        if completed_steps:
                            if previous_state:
                                prev_completed = previous_state.get('completed_steps', []) if isinstance(previous_state, dict) else getattr(previous_state, 'completed_steps', [])
                                # 找出新完成的步骤
                                new_steps = set(completed_steps) - set(prev_completed)
                                for step in new_steps:
                                    # 如果事件中没有包含，才发送
                                    if not any(e.get('type') == 'node_complete' and e.get('node') == step for e in events):
                                        yield json.dumps(
                                            self._create_event(
                                                "node_complete",
                                                step,
                                                f"✅ 完成: {step}"
                                            ),
                                            ensure_ascii=False
                                        )
                            
                        # 检查思考过程
                        if thinking_process:
                            # 发送新的思考过程
                            if previous_state:
                                prev_thinking = previous_state.get('thinking_process', []) if isinstance(previous_state, dict) else getattr(previous_state, 'thinking_process', [])
                                prev_count = len(prev_thinking)
                                new_thoughts = thinking_process[prev_count:]
                                for thought in new_thoughts:
                                    # thinking 事件没有 node 属性，使用简化格式
                                    yield json.dumps({
                                        "type": "thinking",
                                        "data": thought
                                    }, ensure_ascii=False)
                            else:
                                for thought in thinking_process:
                                    # thinking 事件没有 node 属性，使用简化格式
                                    yield json.dumps({
                                        "type": "thinking",
                                        "data": thought
                                    }, ensure_ascii=False)
                        
                        # 检查知识提取
                        if extracted_knowledge and extracted_knowledge.get('entities'):
                            user_msg.extracted_knowledge = extracted_knowledge
                            user_msg.extraction_metadata = {
                                "extraction_time": datetime.now().isoformat(),
                                "stage": conversation_stage
                            }
                            yield json.dumps({
                                "type": "knowledge_extracted",
                                "id": user_msg.id,
                                "data": extracted_knowledge['entities']
                            }, ensure_ascii=False)
                        
                        # 检查下一个问题
                        if next_question:
                            final_state = node_state
                            logger.info(f"✨ 找到下一个问题: {next_question[:50]}...")
                        
                        # 保存当前状态
                        previous_state = node_state
                    
            
            # 在流结束后，检查是否有最终状态
            if final_state:
                next_q = final_state.get('next_question') if isinstance(final_state, dict) else getattr(final_state, 'next_question', None)
                if next_q:
                    logger.info(f"🤖 从最终状态提取问题: {next_q}")
                    async for msg in self._save_and_send_assistant_message(
                        digital_human_id, user_id, next_q
                    ):
                        yield msg
            else:
                # 如果没有从流中获取到状态，尝试直接运行
                logger.debug("没有从流事件中获取到最终状态，尝试直接运行...")
                result = await self.training_graph.ainvoke(state)
                next_question = self._extract_next_question(result)
                
                if next_question:
                    logger.info(f"🤖 从直接运行结果提取问题: {next_question}")
                    async for msg in self._save_and_send_assistant_message(
                        digital_human_id, user_id, next_question
                    ):
                        yield msg
            
            self.training_message_repo.commit()
        except Exception as e:
            logger.error(f"训练对话处理失败: {str(e)}")
            yield json.dumps({
                "type": "error",
                "data": f"处理失败: {str(e)}"
            }, ensure_ascii=False)
    
    
    
    
