"""
抽取知识仓储
处理从文本中抽取的实体和关系
"""

from typing import List, Dict, Any, Optional
import logging
from neomodel import db
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtractedKnowledgeRepository:
    
    def create_entity(self, name: str, entity_type: str, description: str, source_id: Optional[str] = None) -> bool:
        try:
            query = """
            MERGE (e:ExtractedEntity {name: $name})
            SET e.type = $type,
                e.description = $description,
                e.source_id = $source_id,
                e.updated_at = datetime()
            RETURN e
            """
            params = {
                "name": name,
                "type": entity_type,
                "description": description,
                "source_id": source_id or ""
            }
            results, _ = db.cypher_query(query, params)
            return len(results) > 0
        except Exception as e:
            logger.error(f"创建抽取实体失败: {name} - {str(e)}")
            return False
    
    def create_relationship(self, source: str, target: str, description: str, source_id: Optional[str] = None) -> bool:
        try:
            query = """
            MATCH (s:ExtractedEntity {name: $source})
            MATCH (t:ExtractedEntity {name: $target})
            MERGE (s)-[r:EXTRACTED_RELATION]->(t)
            SET r.description = $description,
                r.source_id = $source_id,
                r.updated_at = datetime()
            RETURN r
            """
            params = {
                "source": source,
                "target": target,
                "description": description,
                "source_id": source_id or ""
            }
            results, _ = db.cypher_query(query, params)
            return len(results) > 0
        except Exception as e:
            logger.error(f"创建抽取关系失败: {source} -> {target} - {str(e)}")
            return False
    
    def bulk_create_entities(self, entities: List[Dict[str, Any]], source_id: Optional[str] = None) -> int:
        created_count = 0
        for entity in entities:
            if self.create_entity(
                name=entity.get('name'),
                entity_type=entity.get('type'),
                description=entity.get('description'),
                source_id=source_id
            ):
                created_count += 1
        return created_count
    
    def bulk_create_relationships(self, relationships: List[Dict[str, Any]], source_id: Optional[str] = None) -> int:
        created_count = 0
        for rel in relationships:
            if self.create_relationship(
                source=rel.get('source'),
                target=rel.get('target'),
                description=rel.get('description'),
                source_id=source_id
            ):
                created_count += 1
        return created_count
    
    def find_entities_by_names(self, names: List[str]) -> List[Dict[str, Any]]:
        try:
            query = """
            MATCH (e:ExtractedEntity)
            WHERE e.name IN $names
            RETURN e.name as name, e.type as type, e.description as description
            """
            results, _ = db.cypher_query(query, {"names": names})
            
            entities = []
            for row in results:
                entities.append({
                    "name": row[0],
                    "type": row[1],
                    "description": row[2]
                })
            return entities
        except Exception as e:
            logger.error(f"查找实体失败: {str(e)}")
            return []
    
    def get_entity_context(self, entity_name: str, depth: int = 1) -> Dict[str, Any]:
        try:
            query = """
            MATCH path = (e:ExtractedEntity {name: $name})-[*1..$depth]-(related)
            RETURN e, relationships(path) as rels, collect(distinct related) as related_entities
            LIMIT 10
            """
            results, _ = db.cypher_query(query, {"name": entity_name, "depth": depth})
            
            if results:
                return {
                    "entity": entity_name,
                    "relationships": len(results[0][1]) if results[0][1] else 0,
                    "related_entities": len(results[0][2]) if results[0][2] else 0
                }
            return {}
        except Exception as e:
            logger.error(f"获取实体上下文失败: {str(e)}")
            return {}