from typing import Dict, List, Any, Optional, Union
import logging

from app.repositories.neomodel import (
    GraphRepository,
    ExtractedKnowledgeRepository
)
from app.models.graph.dynamic_entity import DynamicEntity
from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.entity_evolution import EntityEvolutionService

logger = logging.getLogger(__name__)


class GraphService:
    
    def __init__(self):
        self.graph_repo = GraphRepository()
        self.extracted_knowledge_repo = ExtractedKnowledgeRepository()
        self.knowledge_extractor = KnowledgeExtractor()
        self.entity_evolution = EntityEvolutionService()
    
    async def create_entity(
        self, 
        name: str, 
        types: List[str] = None,
        properties: Dict[str, Any] = None,
        description: str = None,
        source: str = None
    ) -> DynamicEntity:
        try:
            entity = DynamicEntity(
                name=name,
                types=types or [],
                properties=properties or {},
                description=description
            )
            
            if source:
                entity.sources.append(source)
            
            success = self.extracted_knowledge_repo.create_entity(
                name=entity.name,
                entity_type="|".join(entity.types) if entity.types else "unknown",
                description=entity.description or "",
                source_id=entity.uid
            )
            
            if success:
                logger.info(f"创建动态实体成功: {name} (类型: {entity.types})")
                return entity
            else:
                logger.error(f"创建动态实体失败: {name}")
                return None
                
        except Exception as e:
            logger.error(f"创建实体异常: {str(e)}")
            raise
    
    async def update_entity(
        self,
        name: str,
        add_types: List[str] = None,
        add_properties: Dict[str, Any] = None,
        new_context: Dict[str, Any] = None,
        source: str = None
    ) -> bool:
        try:
            entities = self.extracted_knowledge_repo.find_entities_by_names([name])
            
            if not entities:
                logger.warning(f"未找到实体: {name}")
                return False
            
            logger.info(f"更新实体: {name}")
            return True
            
        except Exception as e:
            logger.error(f"更新实体失败: {str(e)}")
            return False
    
    async def find_entities(
        self,
        query: str = None,
        entity_types: List[str] = None,
        limit: int = 100
    ) -> List[DynamicEntity]:
        try:
            results = await self.entity_evolution.find_entities(
                name=query,
                entity_type=entity_types[0] if entity_types else None,
                include_extracted=True,
                include_typed=True,
                include_domain=False
            )
            
            entities = []
            for category in ['extracted', 'typed']:
                for item in results.get(category, [])[:limit]:
                    entity = DynamicEntity(
                        name=item['name'],
                        types=[item.get('type', 'unknown')],
                        description=item.get('description'),
                        properties=item.get('attributes', {})
                    )
                    entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"查找实体失败: {str(e)}")
            return []
    
    async def create_relationship(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        try:
            description = properties.get('description', '') if properties else ''
            
            success = self.extracted_knowledge_repo.create_relationship(
                source=source_name,
                target=target_name,
                description=f"{relationship_type}: {description}"
            )
            
            if success:
                logger.info(f"创建关系成功: {source_name} -[{relationship_type}]-> {target_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"创建关系失败: {str(e)}")
            return False
    
    async def extract_and_store_knowledge(
        self,
        text: str,
        source_id: Optional[str] = None
    ) -> Dict:
        try:
            extraction_result = await self.knowledge_extractor.extract(text)
            
            for entity_data in extraction_result['entities']:
                await self.create_entity(
                    name=entity_data['name'],
                    types=[entity_data['type']],
                    description=entity_data.get('description'),
                    source=source_id
                )
            
            for rel_data in extraction_result['relationships']:
                await self.create_relationship(
                    source_name=rel_data['source'],
                    target_name=rel_data['target'],
                    relationship_type=rel_data.get('relation_type', 'RELATED'),
                    properties={'description': rel_data.get('description')}
                )
            
            logger.info(
                f"知识抽取完成: {len(extraction_result['entities'])} 个实体, "
                f"{len(extraction_result['relationships'])} 个关系"
            )
            
            return {
                "success": True,
                "entities_count": len(extraction_result['entities']),
                "relationships_count": len(extraction_result['relationships']),
                "entities": extraction_result['entities'],
                "relationships": extraction_result['relationships']
            }
            
        except Exception as e:
            logger.error(f"知识抽取失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_relevant_context(self, query: str) -> str:
        try:
            extraction = await self.knowledge_extractor.extract(query)
            
            entity_names = [e['name'] for e in extraction['entities']]
            found_entities = self.extracted_knowledge_repo.find_entities_by_names(entity_names)
            
            context_parts = []
            for entity in found_entities:
                context_parts.append(
                    f"相关实体: {entity['name']} ({entity['type']}): {entity['description']}"
                )
                
                entity_context = self.extracted_knowledge_repo.get_entity_context(entity['name'])
                if entity_context:
                    context_parts.append(
                        f"  - 相关连接: {entity_context.get('relationships', 0)} 个关系, "
                        f"{entity_context.get('related_entities', 0)} 个相关实体"
                    )
            
            return "\n".join(context_parts) if context_parts else "暂无相关上下文信息"
            
        except Exception as e:
            logger.error(f"获取上下文失败: {str(e)}")
            return ""
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        return self.graph_repo.get_statistics()
    
    async def find_shortest_path(self, from_name: str, to_name: str) -> Optional[Dict[str, Any]]:
        return self.graph_repo.find_shortest_path(from_name, to_name)
    
    async def list_relationships(
        self,
        relationship_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        return self.graph_repo.list_all_relationships(relationship_type, limit)
    
    async def evolve_entity_to_typed(
        self,
        entity_name: str,
        entity_type: str,
        additional_properties: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        try:
            result = await self.entity_evolution.promote_to_typed(
                entity_name,
                entity_type,
                additional_properties
            )
            
            if result:
                return {
                    "success": True,
                    "entity": result.to_dict(),
                    "message": f"实体 {entity_name} 已升级为类型化实体"
                }
            else:
                return {
                    "success": False,
                    "error": "升级失败"
                }
                
        except Exception as e:
            logger.error(f"实体演化失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def merge_entities(
        self,
        entity_names: List[str],
        target_name: str
    ) -> Dict[str, Any]:
        try:
            success = await self.entity_evolution.merge_duplicates(entity_names, target_name)
            
            if success:
                enriched = await self.entity_evolution.enrich_from_extracted(target_name)
                
                return {
                    "success": True,
                    "merged_entity": target_name,
                    "merged_count": len(entity_names),
                    "entity_info": enriched
                }
            else:
                return {
                    "success": False,
                    "error": "合并失败"
                }
                
        except Exception as e:
            logger.error(f"合并实体失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_entity_evolution_path(self, entity_name: str) -> Dict[str, Any]:
        try:
            path = await self.entity_evolution.get_evolution_path(entity_name)
            
            if path.get('current_level') == 'extracted':
                path['next_step'] = {
                    "level": "typed",
                    "action": "promote_to_typed",
                    "description": "可以升级为类型化实体以获得更好的管理"
                }
            else:
                path['next_step'] = None
            
            return path
            
        except Exception as e:
            logger.error(f"获取演化路径失败: {str(e)}")
            return {"entity_name": entity_name, "error": str(e)}
    
    async def store_digital_human_entity(
        self,
        digital_human_id: int,
        entity: Dict[str, Any]
    ) -> bool:
        """存储数字人的知识实体到图数据库"""
        try:
            import json
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
            
            logger.info(f"存储数字人实体成功: {entity.get('name')} (数字人ID: {digital_human_id})")
            return True
            
        except Exception as e:
            logger.error(f"存储数字人实体失败: {str(e)}")
            return False
    
    async def store_digital_human_relationship(
        self,
        digital_human_id: int,
        relationship: Dict[str, Any]
    ) -> bool:
        """存储数字人的知识关系到图数据库"""
        try:
            import json
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
            
            logger.info(f"存储数字人关系成功: {relationship.get('source')} -> {relationship.get('target')}")
            return True
            
        except Exception as e:
            logger.error(f"存储数字人关系失败: {str(e)}")
            return False
    
    def get_digital_human_knowledge_context(self, digital_human_id: int) -> Dict[str, Any]:
        """获取数字人的知识上下文（同步方法）"""
        try:
            query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            RETURN k.name as name, k.type as type, k.properties as properties
            ORDER BY k.updated_at DESC
            LIMIT 100
            """
            
            results = self.graph_repo.execute_query(query, {"dh_id": digital_human_id})
            
            context = {
                "total_knowledge_points": 0,
                "categories": {},
                "recent_entities": []
            }
            
            for row in results:
                context["total_knowledge_points"] += 1
                
                entity_type = row.get("type", "unknown")
                if entity_type not in context["categories"]:
                    context["categories"][entity_type] = {
                        "count": 0,
                        "examples": []
                    }
                
                context["categories"][entity_type]["count"] += 1
                if len(context["categories"][entity_type]["examples"]) < 3:
                    context["categories"][entity_type]["examples"].append(row.get("name"))
                
                if len(context["recent_entities"]) < 10:
                    context["recent_entities"].append({
                        "name": row.get("name"),
                        "type": entity_type
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"获取数字人知识上下文失败: {str(e)}")
            return {
                "total_knowledge_points": 0,
                "categories": {},
                "recent_entities": []
            }