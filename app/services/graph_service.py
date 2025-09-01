from typing import Dict, List, Any, Optional
import logging

from app.repositories.neomodel import (
    PersonRepository,
    OrganizationRepository,
    GraphRepository,
    ExtractedKnowledgeRepository
)
from app.models.graph.nodes import PersonNode, OrganizationNode
from app.services.knowledge_extractor import KnowledgeExtractor

logger = logging.getLogger(__name__)


class GraphService:
    
    def __init__(self):
        self.person_repo = PersonRepository()
        self.org_repo = OrganizationRepository()
        self.graph_repo = GraphRepository()
        self.extracted_knowledge_repo = ExtractedKnowledgeRepository()
        # 添加知识抽取器
        self.knowledge_extractor = KnowledgeExtractor()
    
    async def create_person(self, person_data: PersonNode) -> PersonNode:
        try:
            neomodel_person = self.person_repo.create_from_pydantic(person_data)
            if neomodel_person:
                logger.info(f"创建人员成功: {person_data.name}")
                return PersonNode.from_neomodel(neomodel_person)
            return None
        except Exception as e:
            logger.error(f"创建人员失败: {str(e)}")
            raise
    
    async def get_person(self, uid: str) -> Optional[PersonNode]:
        person = self.person_repo.find_by_uid(uid)
        if person:
            return PersonNode.from_neomodel(person)
        return None
    
    async def update_person(self, uid: str, person_data: PersonNode) -> Optional[PersonNode]:
        updated = self.person_repo.update_from_pydantic(uid, person_data)
        if updated:
            return PersonNode.from_neomodel(updated)
        return None
    
    async def delete_person(self, uid: str) -> bool:
        return self.person_repo.delete(uid)
    
    async def search_persons(self, keyword: str) -> List[PersonNode]:
        persons = self.person_repo.search(keyword, ["name", "email", "occupation", "bio"])
        return [PersonNode.from_neomodel(p) for p in persons]
    
    async def get_person_network(self, uid: str, depth: int = 2) -> Dict[str, Any]:
        try:
            person = self.person_repo.find_by_uid(uid)
            if not person:
                return None
            
            colleagues = self.person_repo.find_colleagues(uid)
            network = self.person_repo.find_network(uid, depth)
            
            return {
                "person": PersonNode.from_neomodel(person),
                "colleagues": [PersonNode.from_neomodel(c) for c in colleagues],
                "network": [PersonNode.from_neomodel(n) for n in network],
                "stats": {
                    "colleague_count": len(colleagues),
                    "network_size": len(network)
                }
            }
        except Exception as e:
            logger.error(f"获取人员网络失败: {str(e)}")
            return None
    
    
    async def create_organization(self, org_data: OrganizationNode) -> OrganizationNode:
        try:
            neomodel_org = self.org_repo.create_from_pydantic(org_data)
            if neomodel_org:
                logger.info(f"创建组织成功: {org_data.name}")
                return OrganizationNode.from_neomodel(neomodel_org)
            return None
        except Exception as e:
            logger.error(f"创建组织失败: {str(e)}")
            raise
    
    async def get_organization(self, uid: str) -> Optional[OrganizationNode]:
        org = self.org_repo.find_by_uid(uid)
        if org:
            return OrganizationNode.from_neomodel(org)
        return None
    
    async def get_organization_with_employees(self, uid: str) -> Optional[Dict[str, Any]]:
        result = self.org_repo.get_with_employees(uid)
        if result:
            employees = []
            for emp_dict in result['employees']:
                try:
                    emp = PersonNode(**emp_dict)
                    employees.append(emp)
                except:
                    pass
            
            result['employees'] = employees
            return result
        return None
    
    
    async def add_employment(
        self,
        person_uid: str,
        org_uid: str,
        position: str,
        department: str = None
    ) -> bool:
        try:
            person = self.person_repo.find_by_uid(person_uid)
            org = self.org_repo.find_by_uid(org_uid)
            
            if person and org:
                rel = person.works_at.connect(org)
                if rel:
                    rel.position = position
                    rel.department = department
                    rel.save()
                logger.info(f"添加雇佣关系: {person_uid} -> {org_uid}")
                return True
            return False
        except Exception as e:
            logger.error(f"添加雇佣关系失败: {str(e)}")
            return False
    
    async def add_friendship(self, person1_identifier: str, person2_identifier: str) -> bool:
        logger.info(f"服务层: 进入add_friendship方法")
        try:
            import re
            
            uuid_pattern = re.compile(r'^[a-f0-9]{32}$')
            
            person1_uid = person1_identifier
            if not uuid_pattern.match(person1_identifier):
                persons = self.person_repo.find_by_name(person1_identifier)
                if persons:
                    person1_uid = persons[0].uid
                    logger.info(f"服务层: 将名字 {person1_identifier} 转换为UID: {person1_uid}")
                else:
                    logger.error(f"服务层: 找不到人物: {person1_identifier}")
                    return False
            
            person2_uid = person2_identifier
            if not uuid_pattern.match(person2_identifier):
                persons = self.person_repo.find_by_name(person2_identifier)
                if persons:
                    person2_uid = persons[0].uid
                    logger.info(f"服务层: 将名字 {person2_identifier} 转换为UID: {person2_uid}")
                else:
                    logger.error(f"服务层: 找不到人物: {person2_identifier}")
                    return False
            
            logger.info(f"服务层: 开始添加朋友关系 {person1_uid} <-> {person2_uid}")
            
            person1 = self.person_repo.find_by_uid(person1_uid)
            person2 = self.person_repo.find_by_uid(person2_uid)
            
            if not person1:
                logger.error(f"服务层: UID {person1_uid} 对应的人物不存在")
                return False
            
            if not person2:
                logger.error(f"服务层: UID {person2_uid} 对应的人物不存在")
                return False
            
            logger.info(f"服务层: 找到两个人物 - {person1.name} 和 {person2.name}")
            
            try:
                if not hasattr(person1, 'friends'):
                    logger.error(f"服务层: Person1没有friends属性")
                    return False
                
                rel = person1.friends.connect(person2)
                
                if rel:
                    rel.save()
                    logger.info(f"服务层: 成功添加朋友关系: {person1.name} <-> {person2.name}")
                    return True
                
                return False
                
            except AttributeError as ae:
                logger.error(f"服务层: 属性错误 - {str(ae)}")
                return False
            except Exception as inner_e:
                logger.error(f"服务层: 连接关系时出错 - {str(inner_e)}")
                return False
            
        except Exception as e:
            logger.exception(f"服务层: 添加朋友关系异常: {str(e)}")
            return False
    
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        return self.graph_repo.get_statistics()
    
    async def find_shortest_path(self, from_uid: str, to_uid: str) -> Optional[Dict[str, Any]]:
        return self.graph_repo.find_shortest_path(from_uid, to_uid)
    
    async def list_relationships(self, relationship_type: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        return self.graph_repo.list_all_relationships(relationship_type, limit)
    
    async def extract_and_store_knowledge(self, text: str, source_id: Optional[str] = None) -> Dict:
        """
        内部方法：从文本抽取知识并存储（使用 Repository）
        供对话服务等其他服务调用
        """
        try:
            # 1. 抽取
            extraction_result = await self.knowledge_extractor.extract(text)
            
            # 2. 使用 Repository 存储
            stored_entities = self.extracted_knowledge_repo.bulk_create_entities(
                extraction_result['entities'],
                source_id
            )
            
            stored_relationships = self.extracted_knowledge_repo.bulk_create_relationships(
                extraction_result['relationships'],
                source_id
            )
            
            logger.info(f"知识抽取完成: 存储了 {stored_entities} 个实体, {stored_relationships} 个关系")
            
            return {
                "success": True,
                "entities_count": len(extraction_result['entities']),
                "relationships_count": len(extraction_result['relationships']),
                "stored_entities": stored_entities,
                "stored_relationships": stored_relationships
            }
            
        except Exception as e:
            logger.error(f"知识抽取失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_relevant_context(self, query: str) -> str:
        """
        内部方法：根据查询获取相关上下文（使用 Repository）
        供对话服务使用
        """
        try:
            # 1. 从查询中抽取关键实体
            extraction = await self.knowledge_extractor.extract(query)
            
            # 2. 使用 Repository 查询
            entity_names = [e['name'] for e in extraction['entities']]
            found_entities = self.extracted_knowledge_repo.find_entities_by_names(entity_names)
            
            # 3. 构建上下文
            context_parts = []
            for entity in found_entities:
                context_parts.append(
                    f"相关实体: {entity['name']} ({entity['type']}): {entity['description']}"
                )
                
                # 获取更多上下文
                entity_context = self.extracted_knowledge_repo.get_entity_context(entity['name'])
                if entity_context:
                    context_parts.append(
                        f"  - 相关实体数: {entity_context.get('related_entities', 0)}"
                    )
            
            return "\n".join(context_parts) if context_parts else "暂无相关上下文信息"
            
        except Exception as e:
            logger.error(f"获取上下文失败: {str(e)}")
            return ""