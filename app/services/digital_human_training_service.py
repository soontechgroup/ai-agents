from typing import Dict, List, Any, Generator, Optional, AsyncGenerator
import json
from datetime import datetime
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.graph_service import GraphService
from app.core.models import DigitalHumanTrainingMessage
from app.core.logger import logger
from app.repositories.neomodel import GraphRepository
from app.core.config import settings


class TrainingState(BaseModel):
    messages: List[BaseMessage] = []
    digital_human_id: int
    user_id: int
    current_message: str = ""
    extracted_knowledge: Dict[str, Any] = {}
    knowledge_context: Dict[str, Any] = {}
    intent: str = ""
    next_question: str = ""
    should_extract: bool = False
    should_explore_deeper: bool = False
    conversation_stage: str = "initial"
    total_knowledge_points: int = 0
    categories: Dict[str, Any] = {}
    current_step: str = ""
    completed_steps: List[str] = []
    step_results: Dict[str, Any] = {}
    thinking_process: List[str] = []
    events: List[Dict[str, Any]] = []  # 事件队列，用于流式通知


class DigitalHumanTrainingService:
    
    def __init__(
        self,
        db: Session,
        knowledge_extractor: KnowledgeExtractor,
        graph_service: GraphService
    ):
        self.db = db
        self.knowledge_extractor = knowledge_extractor
        self.graph_service = graph_service
        self.graph_repo = GraphRepository()
        
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.7
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
            self._route_by_intent,
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
    
    def save_graph_visualization(self, output_dir: str = "graph_visualizations"):
        """保存工作流图的可视化"""
        import os
        from datetime import datetime
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取图对象
        graph = self.training_graph.get_graph()
        
        # 1. 尝试生成 PNG 图片
        try:
            png_data = graph.draw_png()
            png_path = f"{output_dir}/training_graph.png"
            with open(png_path, "wb") as f:
                f.write(png_data)
            logger.info(f"✅ 图已保存为 PNG: {png_path}")
            return png_path
        except Exception as e:
            logger.warning(f"⚠️ 无法生成 PNG（可能需要安装 graphviz）: {e}")
        
        # 2. 如果 PNG 失败，至少保存 Mermaid
        try:
            mermaid_text = graph.draw_mermaid()
            mermaid_path = f"{output_dir}/training_graph.mmd"
            with open(mermaid_path, "w") as f:
                f.write(mermaid_text)
            logger.info(f"✅ 图已保存为 Mermaid: {mermaid_path}")
            logger.info("📊 可在 https://mermaid.live 查看")
            return mermaid_path
        except Exception as e:
            logger.error(f"❌ 无法生成任何可视化: {e}")
            return None
    
    def get_graph_ascii(self) -> str:
        """获取 ASCII 格式的图"""
        try:
            graph = self.training_graph.get_graph()
            return graph.print_ascii()
        except Exception as e:
            logger.error(f"无法生成 ASCII 图: {e}")
            return "无法生成 ASCII 图"
    
    def get_graph_mermaid(self) -> str:
        """获取 Mermaid 格式的图"""
        try:
            graph = self.training_graph.get_graph()
            return graph.draw_mermaid()
        except Exception as e:
            logger.error(f"无法生成 Mermaid 图: {e}")
            return "无法生成 Mermaid 图"
    
    def _recognize_intent(self, state: TrainingState) -> TrainingState:
        # 节点开始事件
        state.events.append({
            "type": "node_start",
            "node": "intent_recognition",
            "message": "🔍 开始分析用户意图...",
            "timestamp": datetime.now().isoformat()
        })
        
        state.current_step = "recognizing_intent"
        state.thinking_process.append("正在分析用户消息意图...")
        
        # 添加思考步骤
        state.events.append({
            "type": "thinking",
            "node": "intent_recognition",
            "message": "💭 解析消息内容，识别关键信息...",
            "timestamp": datetime.now().isoformat()
        })
        
        prompt = f"""
分析以下用户消息的意图和内容类型：

用户消息: {state.current_message}

请判断：
1. 意图类型（information_sharing/question_asking/clarification/greeting/other）
2. 是否包含可提取的知识（yes/no）
3. 当前对话阶段（initial/exploring/deepening/concluding）

返回JSON格式：
{{
    "intent": "...",
    "has_knowledge": true/false,
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
        
        state.intent = result.get("intent", "other")
        state.should_extract = result.get("has_knowledge", False)
        state.conversation_stage = result.get("stage", "exploring")
        
        state.step_results["intent_recognition"] = {
            "intent": state.intent,
            "should_extract": state.should_extract,
            "stage": state.conversation_stage
        }
        
        # 节点完成事件
        state.events.append({
            "type": "node_complete",
            "node": "intent_recognition",
            "message": f"✅ 意图识别完成: {state.intent}",
            "result": {
                "intent": state.intent,
                "stage": state.conversation_stage,
                "should_extract": state.should_extract
            },
            "timestamp": datetime.now().isoformat()
        })
        
        state.completed_steps.append("intent_recognition")
        state.thinking_process.append(f"识别到意图: {state.intent}, 对话阶段: {state.conversation_stage}")
        return state
    
    def _route_by_intent(self, state: TrainingState) -> str:
        if state.should_extract:
            return "extract"
        elif state.total_knowledge_points > 5:
            return "analyze"
        else:
            return "direct"
    
    async def _extract_knowledge(self, state: TrainingState) -> TrainingState:
        state.current_step = "extracting_knowledge"
        state.thinking_process.append("正在提取知识点...")
        
        if not state.should_extract:
            state.extracted_knowledge = {"entities": [], "relationships": []}
            state.completed_steps.append("knowledge_extraction")
            return state
        
        extraction_result = await self.knowledge_extractor.extract(state.current_message)
        state.extracted_knowledge = extraction_result
        
        entity_count = len(extraction_result.get("entities", []))
        relationship_count = len(extraction_result.get("relationships", []))
        
        for entity in extraction_result.get("entities", []):
            await self._store_entity_to_graph(state.digital_human_id, entity)
        
        for relationship in extraction_result.get("relationships", []):
            await self._store_relationship_to_graph(state.digital_human_id, relationship)
        
        state.step_results["knowledge_extraction"] = {
            "entities_count": entity_count,
            "relationships_count": relationship_count,
            "extracted": extraction_result
        }
        
        state.completed_steps.append("knowledge_extraction")
        state.thinking_process.append(f"提取到 {entity_count} 个实体, {relationship_count} 个关系")
        return state
    
    def _analyze_context(self, state: TrainingState) -> TrainingState:
        state.current_step = "analyzing_context"
        state.thinking_process.append("正在分析知识图谱上下文...")
        
        context = self._get_current_context(state.digital_human_id)
        state.knowledge_context = context
        state.total_knowledge_points = context.get("total_knowledge_points", 0)
        state.categories = context.get("categories", {})
        
        if state.total_knowledge_points > 20 and not state.categories.get("hobby"):
            state.should_explore_deeper = True
        elif state.total_knowledge_points > 10 and len(state.categories) < 3:
            state.should_explore_deeper = True
        
        state.step_results["context_analysis"] = {
            "total_points": state.total_knowledge_points,
            "categories_count": len(state.categories),
            "should_explore_deeper": state.should_explore_deeper
        }
        
        state.completed_steps.append("context_analysis")
        state.thinking_process.append(f"已了解 {state.total_knowledge_points} 个知识点，涵盖 {len(state.categories)} 个领域")
        return state
    
    def _generate_question(self, state: TrainingState) -> TrainingState:
        state.current_step = "generating_question"
        state.thinking_process.append("正在生成引导性问题...")
        
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
        state.next_question = response.content.strip()
        
        state.step_results["question_generation"] = {
            "question": state.next_question,
            "based_on_stage": state.conversation_stage
        }
        
        state.completed_steps.append("question_generation")
        state.thinking_process.append("已生成引导性问题")
        return state
    
    def _build_context_prompt(self, state: TrainingState) -> str:
        prompt_parts = []
        
        if state.current_message:
            prompt_parts.append(f"用户刚才说: {state.current_message}")
        
        if state.extracted_knowledge.get("entities"):
            entities = state.extracted_knowledge["entities"]
            entity_names = [e.get("name") for e in entities[:3]]
            prompt_parts.append(f"提取到的实体: {', '.join(entity_names)}")
        
        if state.total_knowledge_points > 0:
            prompt_parts.append(f"已了解的知识点数: {state.total_knowledge_points}")
        
        if state.categories:
            cat_summary = []
            for cat, info in state.categories.items():
                if isinstance(info, dict) and info.get("count"):
                    cat_summary.append(f"{cat}({info['count']}个)")
            if cat_summary:
                prompt_parts.append(f"已了解的领域: {', '.join(cat_summary)}")
        
        prompt_parts.append(f"当前对话阶段: {state.conversation_stage}")
        
        return "\n".join(prompt_parts)
    
    async def _save_message(self, state: TrainingState) -> TrainingState:
        pass
    
    def _get_current_context(self, digital_human_id: int) -> Dict[str, Any]:
        try:
            query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            WITH k, 
                 CASE 
                   WHEN k.type IN ['person', 'profession'] THEN 'profession'
                   WHEN k.type IN ['skill', 'technology'] THEN 'skill'
                   WHEN k.type IN ['project', 'product'] THEN 'project'
                   WHEN k.type IN ['organization', 'company'] THEN 'organization'
                   WHEN k.type IN ['hobby', 'interest'] THEN 'hobby'
                   ELSE 'other'
                 END as category
            RETURN category, collect(k.name) as items, count(k) as count
            """
            
            results = self.graph_repo.execute_query(query, {"dh_id": digital_human_id})
            
            context = {
                "total_knowledge_points": 0,
                "categories": {},
                "recent_entities": []
            }
            
            for row in results:
                category = row[0]
                items = row[1]
                count = row[2]
                context["categories"][category] = {
                    "count": count,
                    "items": items[:5]
                }
                context["total_knowledge_points"] += count
            
            return context
            
        except Exception as e:
            logger.error(f"获取训练上下文失败: {str(e)}")
            return {"total_knowledge_points": 0, "categories": {}}
    
    async def _save_and_send_assistant_message(
        self,
        digital_human_id: int,
        user_id: int,
        question: str
    ) -> AsyncGenerator[str, None]:
        """保存助手消息并发送事件"""
        assistant_msg = DigitalHumanTrainingMessage(
            digital_human_id=digital_human_id,
            user_id=user_id,
            role="assistant",
            content=question
        )
        self.db.add(assistant_msg)
        self.db.flush()
        
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
            user_msg = DigitalHumanTrainingMessage(
                digital_human_id=digital_human_id,
                user_id=user_id,
                role="user",
                content=user_message
            )
            self.db.add(user_msg)
            self.db.flush()
            
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
                # chunk 是状态更新
                if chunk:
                    logger.debug(f"📊 状态更新: {list(chunk.keys()) if isinstance(chunk, dict) else type(chunk)}")
                    
                    # 检测新完成的步骤
                    if isinstance(chunk, dict):
                        # 检查是否有新完成的步骤
                        if 'completed_steps' in chunk:
                            if previous_state and 'completed_steps' in previous_state:
                                # 找出新完成的步骤
                                new_steps = set(chunk['completed_steps']) - set(previous_state.get('completed_steps', []))
                                for step in new_steps:
                                    yield json.dumps({
                                        "type": "node_complete",
                                        "node": step,
                                        "data": f"✅ 完成: {step}",
                                        "timestamp": datetime.now().isoformat()
                                    }, ensure_ascii=False)
                            
                        # 检查思考过程
                        if 'thinking_process' in chunk and chunk['thinking_process']:
                            # 发送新的思考过程
                            if previous_state and 'thinking_process' in previous_state:
                                prev_count = len(previous_state.get('thinking_process', []))
                                new_thoughts = chunk['thinking_process'][prev_count:]
                                for thought in new_thoughts:
                                    yield json.dumps({
                                        "type": "thinking",
                                        "data": thought
                                    }, ensure_ascii=False)
                            else:
                                for thought in chunk.get('thinking_process', []):
                                    yield json.dumps({
                                        "type": "thinking",
                                        "data": thought
                                    }, ensure_ascii=False)
                        
                        # 检查意图识别
                        if 'intent' in chunk and chunk['intent']:
                            yield json.dumps({
                                "type": "intent_recognized",
                                "data": chunk['intent']
                            }, ensure_ascii=False)
                        
                        # 检查知识提取
                        if 'extracted_knowledge' in chunk and chunk['extracted_knowledge'].get('entities'):
                            user_msg.extracted_knowledge = chunk['extracted_knowledge']
                            user_msg.extraction_metadata = {
                                "extraction_time": datetime.now().isoformat(),
                                "intent": chunk.get('intent', ''),
                                "stage": chunk.get('conversation_stage', '')
                            }
                            yield json.dumps({
                                "type": "knowledge_extracted",
                                "id": user_msg.id,
                                "data": chunk['extracted_knowledge']['entities']
                            }, ensure_ascii=False)
                        
                        # 检查下一个问题
                        if 'next_question' in chunk and chunk['next_question']:
                            final_state = chunk
                            logger.info(f"✨ 找到下一个问题: {chunk['next_question'][:50]}...")
                        
                        # 保存当前状态作为上一个状态
                        previous_state = chunk
                    
            
            # 在流结束后，检查是否有最终状态
            if final_state and "next_question" in final_state:
                logger.info(f"🤖 从最终状态提取问题: {final_state['next_question']}")
                async for msg in self._save_and_send_assistant_message(
                    digital_human_id, user_id, final_state['next_question']
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
            
            self.db.commit()
        except Exception as e:
            logger.error(f"训练对话处理失败: {str(e)}")
            yield json.dumps({
                "type": "error",
                "data": f"处理失败: {str(e)}"
            }, ensure_ascii=False)
    
    
    async def _store_entity_to_graph(
        self,
        digital_human_id: int,
        entity: Dict[str, Any]
    ):
        try:
            query = """
            MERGE (dh:DigitalHuman {id: $dh_id})
            MERGE (k:Knowledge {
                name: $name,
                digital_human_id: $dh_id
            })
            SET k.type = $type,
                k.types = $types,
                k.confidence = $confidence,
                k.properties = $properties,
                k.updated_at = datetime()
            MERGE (dh)-[r:HAS_KNOWLEDGE]->(k)
            SET r.updated_at = datetime()
            """
            
            self.graph_repo.execute_query(query, {
                "dh_id": digital_human_id,
                "name": entity.get("name"),
                "type": entity.get("type", "unknown"),
                "types": json.dumps(entity.get("types", [])),
                "confidence": entity.get("confidence", 0.5),
                "properties": json.dumps(entity.get("properties", {}))
            })
            
        except Exception as e:
            logger.error(f"存储实体到图数据库失败: {str(e)}")
    
    async def _store_relationship_to_graph(
        self,
        digital_human_id: int,
        relationship: Dict[str, Any]
    ):
        try:
            query = """
            MATCH (k1:Knowledge {
                name: $source,
                digital_human_id: $dh_id
            })
            MATCH (k2:Knowledge {
                name: $target,
                digital_human_id: $dh_id
            })
            MERGE (k1)-[r:RELATES_TO]->(k2)
            SET r.relation_type = $relation_type,
                r.confidence = $confidence,
                r.properties = $properties,
                r.updated_at = datetime()
            """
            
            self.graph_repo.execute_query(query, {
                "dh_id": digital_human_id,
                "source": relationship.get("source"),
                "target": relationship.get("target"),
                "relation_type": relationship.get("relation_type"),
                "confidence": relationship.get("confidence", 0.5),
                "properties": json.dumps(relationship.get("properties", {}))
            })
            
        except Exception as e:
            logger.error(f"存储关系到图数据库失败: {str(e)}")
    
    
    
