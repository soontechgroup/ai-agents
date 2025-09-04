from typing import Dict, List, Any, Generator, Optional
import json
import time
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.graph_service import GraphService
from app.core.models import DigitalHuman, DigitalHumanTrainingMessage
from app.core.logger import logger
from app.repositories.neomodel import GraphRepository
from app.core.config import settings


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
        
        self.question_templates = {
            "初次了解": [
                "让我更了解你一些。你的职业背景是什么？",
                "你最擅长的领域是什么？",
                "可以介绍一下你自己吗？",
                "你的主要工作内容是什么？"
            ],
            "深入职业": [
                "你在{profession}这个职业中最有成就感的项目是什么？",
                "作为{profession}，你通常使用哪些工具和技术？",
                "在{profession}领域，你有什么独特的经验？",
                "你是如何成为{profession}的？"
            ],
            "探索技能": [
                "你提到了{skill}，能具体说说你是如何应用它的吗？",
                "在{skill}方面，你有什么独特的经验或见解？",
                "学习{skill}的过程中，你遇到过什么挑战？",
                "{skill}对你的工作有什么帮助？"
            ],
            "项目经验": [
                "能详细介绍一下{project}这个项目吗？",
                "{project}项目中最大的挑战是什么？",
                "{project}项目的成果如何？",
                "在{project}项目中你承担了什么角色？"
            ],
            "关联发现": [
                "你的{domain1}经验对{domain2}有什么影响吗？",
                "{skill1}和{skill2}之间有什么联系吗？",
                "这些经历之间有什么共同点吗？"
            ],
            "个人发展": [
                "你的职业规划是什么？",
                "你最近在学习什么新技术或技能？",
                "什么激励着你在这个领域发展？",
                "你的职业目标是什么？"
            ],
            "兴趣爱好": [
                "工作之外，你有什么兴趣爱好吗？",
                "你平时喜欢做什么来放松？",
                "有什么特别的爱好想分享吗？"
            ]
        }
    
    async def process_training_conversation(
        self,
        digital_human_id: int,
        user_message: str,
        user_id: int
    ) -> Generator[str, None, None]:
        try:
            # 如果是开始训练的消息
            if user_message.strip() in ["开始训练", "开始", "start", "begin", "你好"]:
                question = self._get_initial_question()
                
                # 保存助手的初始问题
                assistant_msg = DigitalHumanTrainingMessage(
                    digital_human_id=digital_human_id,
                    user_id=user_id,
                    role="assistant",
                    content=question
                )
                self.db.add(assistant_msg)
                self.db.flush()  # 获取ID
                self.db.commit()
                
                yield json.dumps({
                    "type": "assistant_question",
                    "id": assistant_msg.id,
                    "data": question
                }, ensure_ascii=False)
                return
            
            # 记录提取开始时间
            extraction_start = time.time()
            
            # 保存用户消息
            user_msg = DigitalHumanTrainingMessage(
                digital_human_id=digital_human_id,
                user_id=user_id,
                role="user",
                content=user_message
            )
            self.db.add(user_msg)
            self.db.flush()  # 获取用户消息ID
            
            # 返回用户消息确认
            yield json.dumps({
                "type": "user_message",
                "id": user_msg.id,
                "data": user_message
            }, ensure_ascii=False)
            
            # 抽取知识
            knowledge_result = await self._extract_and_store_knowledge(
                digital_human_id, user_message, extraction_start
            )
            
            # 更新用户消息的抽取知识和元数据
            if knowledge_result["entities"] or knowledge_result["relationships"]:
                user_msg.extracted_knowledge = {
                    "entities": knowledge_result["entities"],
                    "relationships": knowledge_result["relationships"]
                }
                user_msg.extraction_metadata = knowledge_result.get("metadata", {})
            
            # 如果抽取到了知识，返回给前端
            if knowledge_result["entities"]:
                yield json.dumps({
                    "type": "knowledge_extracted",
                    "id": user_msg.id,  # 关联的用户消息ID
                    "data": knowledge_result["entities"]
                }, ensure_ascii=False)
            
            # 获取训练上下文
            current_context = await self._get_training_context(digital_human_id)
            
            # 生成下一个问题
            next_question = await self._generate_next_question(
                digital_human_id, current_context, knowledge_result
            )
            
            # 保存助手消息
            assistant_msg = DigitalHumanTrainingMessage(
                digital_human_id=digital_human_id,
                user_id=user_id,
                role="assistant",
                content=next_question
            )
            self.db.add(assistant_msg)
            self.db.flush()  # 获取助手消息ID
            
            # 提交所有更改
            self.db.commit()
            
            yield json.dumps({
                "type": "assistant_question",
                "id": assistant_msg.id,
                "data": next_question
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"训练对话处理失败: {str(e)}")
            yield json.dumps({
                "type": "error",
                "data": "处理失败，请重试"
            }, ensure_ascii=False)
    
    async def _extract_and_store_knowledge(
        self,
        digital_human_id: int,
        message: str,
        start_time: float
    ) -> Dict[str, Any]:
        try:
            # 抽取知识
            extraction_result = await self.knowledge_extractor.extract(message)
            
            # 构建提取元数据
            metadata = {
                "extraction_process": {
                    "model": settings.LLM_MODEL,
                    "method": "GraphRAG",
                    "timestamp": datetime.now().isoformat(),
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                },
                "quality_metrics": {
                    "entities_found": len(extraction_result.get("entities", [])),
                    "relationships_found": len(extraction_result.get("relationships", [])),
                    "confidence_scores": {
                        "entity_extraction": 0.85,  # 可以从实际抽取结果中获取
                        "relationship_extraction": 0.75
                    }
                },
                "context": {
                    "message_count": self._get_message_count(digital_human_id),
                    "current_topic": self._detect_topic(message)
                }
            }
            
            # 存储实体到Neo4j
            for entity in extraction_result["entities"]:
                await self._store_entity_to_graph(digital_human_id, entity)
            
            # 存储关系到Neo4j
            for relationship in extraction_result["relationships"]:
                await self._store_relationship_to_graph(digital_human_id, relationship)
            
            # 返回结果包含元数据
            extraction_result["metadata"] = metadata
            return extraction_result
            
        except Exception as e:
            logger.error(f"知识抽取失败: {str(e)}")
            return {
                "entities": [],
                "relationships": [],
                "metadata": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
    
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
    
    async def _get_training_context(
        self,
        digital_human_id: int
    ) -> Dict[str, Any]:
        try:
            query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            WITH k, 
                 CASE 
                   WHEN k.type IN ['person', 'profession'] THEN 'profession'
                   WHEN k.type IN ['skill', 'technology'] THEN 'skill'
                   WHEN k.type IN ['project', 'product'] THEN 'project'
                   WHEN k.type IN ['organization', 'company'] THEN 'organization'
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
    
    async def _generate_next_question(
        self,
        digital_human_id: int,
        context: Dict[str, Any],
        last_extraction: Dict[str, Any]
    ) -> str:
        try:
            total_points = context.get("total_knowledge_points", 0)
            categories = context.get("categories", {})
            last_entities = last_extraction.get("entities", [])
            
            # 如果还没有任何知识点，使用初始问题
            if total_points == 0:
                return self._get_initial_question()
            
            # 初期阶段（少于5个知识点），探索基础信息
            if total_points < 5:
                if not categories.get("profession"):
                    return self.question_templates["初次了解"][0]
                else:
                    return self.question_templates["初次了解"][1]
            
            # 如果刚刚提取到实体，基于实体生成深入问题
            if last_entities:
                last_entity = last_entities[0]
                entity_name = last_entity.get("name")
                entity_type = last_entity.get("type", "").lower()
                
                # 根据实体类型生成相应问题
                if entity_type in ["person", "profession"]:
                    return self.question_templates["深入职业"][0].format(
                        profession=entity_name
                    )
                
                elif entity_type in ["skill", "technology"]:
                    return self.question_templates["探索技能"][0].format(
                        skill=entity_name
                    )
                
                elif entity_type in ["project", "product"]:
                    return self.question_templates["项目经验"][0].format(
                        project=entity_name
                    )
            
            # 探索缺失的领域
            if not categories.get("project") and categories.get("profession"):
                return "能介绍一些你参与过的具体项目吗？"
            
            if not categories.get("skill") and categories.get("profession"):
                return "你在工作中主要使用哪些技术或工具？"
            
            # 中期阶段（20个知识点以上），探索兴趣爱好
            if total_points > 20 and not categories.get("other"):
                return self.question_templates["兴趣爱好"][0]
            
            # 探索个人发展
            if total_points > 15:
                return self.question_templates["个人发展"][0]
            
            # 发现关联
            if categories.get("skill") and categories.get("project"):
                skills = categories["skill"]["items"][:2]
                if len(skills) >= 2:
                    return self.question_templates["关联发现"][1].format(
                        skill1=skills[0],
                        skill2=skills[1]
                    )
            
            # 默认问题
            return "还有什么其他方面的经历或技能想要分享吗？"
            
        except Exception as e:
            logger.error(f"生成问题失败: {str(e)}")
            return "能再多介绍一些你自己吗？"
    
    def _get_initial_question(self) -> str:
        """获取初始问题"""
        return self.question_templates["初次了解"][2]
    
    def _get_message_count(self, digital_human_id: int) -> int:
        """获取消息数量"""
        try:
            count = self.db.query(DigitalHumanTrainingMessage).filter(
                DigitalHumanTrainingMessage.digital_human_id == digital_human_id
            ).count()
            return count
        except:
            return 0
    
    def _detect_topic(self, message: str) -> str:
        """检测消息主题"""
        # 简单的关键词匹配，可以后续改进
        topics = {
            "职业": ["工作", "职业", "公司", "岗位", "职位"],
            "技能": ["技术", "技能", "工具", "语言", "框架"],
            "项目": ["项目", "产品", "系统", "开发", "实现"],
            "教育": ["学习", "学校", "专业", "课程", "培训"],
            "兴趣": ["爱好", "兴趣", "喜欢", "休闲", "娱乐"]
        }
        
        for topic, keywords in topics.items():
            for keyword in keywords:
                if keyword in message:
                    return topic
        
        return "其他"