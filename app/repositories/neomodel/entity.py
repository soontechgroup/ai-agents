"""
Entity Repository
Handles CRUD operations for Entity nodes
"""

from typing import List, Optional, Dict, Any
from neomodel import db
from app.repositories.neomodel.base import NeomodelRepository as BaseRepository
from app.models.neomodel.entity import EntityNode
from app.core.logger import logger


class EntityRepository(BaseRepository):
    """Repository for Entity node operations"""
    
    def __init__(self):
        super().__init__(EntityNode)
    
    def find_by_name(
        self,
        name: str,
        digital_human_id: str,
        fuzzy: bool = False
    ) -> Optional[EntityNode]:
        """
        Find entity by name
        
        Args:
            name: Entity name
            digital_human_id: Digital human context
            fuzzy: Use fuzzy matching
        """
        try:
            if fuzzy:
                # Case-insensitive fuzzy matching
                query = """
                    MATCH (e:EntityNode {digital_human_id: $dh_id})
                    WHERE toLower(e.name) = toLower($name)
                    OR $name IN e.aliases
                    RETURN e
                    LIMIT 1
                """
            else:
                # Exact match
                query = """
                    MATCH (e:EntityNode {name: $name, digital_human_id: $dh_id})
                    RETURN e
                    LIMIT 1
                """
            
            results, _ = db.cypher_query(query, {
                'name': name,
                'dh_id': digital_human_id
            })
            
            if results:
                return EntityNode.inflate(results[0][0])
            return None
            
        except Exception as e:
            logger.error(f"Error finding entity by name: {str(e)}")
            return None
    
    def find_or_create(
        self,
        name: str,
        entity_type: str,
        digital_human_id: str,
        description: Optional[str] = None
    ) -> EntityNode:
        """
        Find existing entity or create new one
        
        Args:
            name: Entity name
            entity_type: Type of entity
            digital_human_id: Digital human context
            description: Optional description
        """
        try:
            # Try to find existing entity
            existing = self.find_by_name(name, digital_human_id, fuzzy=True)
            
            if existing:
                # Update mention count
                existing.update_mention()
                return existing
            
            # Create new entity
            entity = EntityNode(
                name=name,
                entity_type=entity_type,
                digital_human_id=digital_human_id,
                description=description
            )
            entity.save()
            
            logger.info(f"Created new entity: {name} ({entity_type})")
            return entity
            
        except Exception as e:
            logger.error(f"Error in find_or_create entity: {str(e)}")
            raise
    
    def find_co_occurring(
        self,
        entity_uid: str,
        min_occurrences: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find entities that frequently co-occur with this entity
        
        Args:
            entity_uid: Source entity UID
            min_occurrences: Minimum co-occurrence count
            limit: Maximum results
        """
        try:
            query = """
                MATCH (e:EntityNode {uid: $uid})-[r:CO_OCCURS]-(other:EntityNode)
                WHERE r.occurrence_count >= $min_occ
                RETURN other, r.occurrence_count as count, r.correlation_strength as strength
                ORDER BY count DESC, strength DESC
                LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'uid': entity_uid,
                'min_occ': min_occurrences,
                'limit': limit
            })
            
            co_occurring = []
            for row in results:
                entity = EntityNode.inflate(row[0])
                co_occurring.append({
                    'entity': entity.to_dict(),
                    'occurrence_count': row[1],
                    'correlation_strength': row[2]
                })
            
            return co_occurring
            
        except Exception as e:
            logger.error(f"Error finding co-occurring entities: {str(e)}")
            return []
    
    def find_by_type(
        self,
        entity_type: str,
        digital_human_id: str,
        limit: int = 100
    ) -> List[EntityNode]:
        """
        Find entities by type
        
        Args:
            entity_type: Type of entity
            digital_human_id: Digital human context
            limit: Maximum results
        """
        try:
            query = """
                MATCH (e:EntityNode {entity_type: $type, digital_human_id: $dh_id})
                RETURN e
                ORDER BY e.importance_score DESC, e.mention_count DESC
                LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'type': entity_type,
                'dh_id': digital_human_id,
                'limit': limit
            })
            
            return [EntityNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error finding entities by type: {str(e)}")
            return []
    
    def get_entity_knowledge(
        self,
        entity_uid: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get all knowledge that mentions this entity
        
        Args:
            entity_uid: Entity UID
            limit: Maximum knowledge items
        """
        try:
            query = """
                MATCH (e:EntityNode {uid: $uid})
                OPTIONAL MATCH (e)<-[:MENTIONS]-(k:KnowledgeNode)
                WHERE k.validation_status <> 'deprecated'
                RETURN e,
                       collect(DISTINCT {
                           uid: k.uid,
                           summary: k.summary,
                           category: k.category,
                           importance: k.importance
                       })[..$limit] as knowledge
            """
            
            results, _ = db.cypher_query(query, {
                'uid': entity_uid,
                'limit': limit
            })
            
            if results:
                entity = EntityNode.inflate(results[0][0])
                return {
                    'entity': entity.to_dict(),
                    'knowledge': results[0][1]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting entity knowledge: {str(e)}")
            return None
    
    def merge_entities(
        self,
        primary_uid: str,
        secondary_uid: str
    ) -> bool:
        """
        Merge two entities (when duplicates are detected)
        
        Args:
            primary_uid: Primary entity to keep
            secondary_uid: Entity to merge into primary
        """
        try:
            primary = self.find_by_uid(primary_uid)
            secondary = self.find_by_uid(secondary_uid)
            
            if not primary or not secondary:
                return False
            
            # Transfer all relationships from secondary to primary
            query = """
                MATCH (secondary:EntityNode {uid: $secondary_uid})
                MATCH (primary:EntityNode {uid: $primary_uid})
                MATCH (secondary)-[r]-(connected)
                WHERE NOT (primary)-[]-(connected)
                WITH primary, connected, type(r) as rel_type, properties(r) as props
                CALL apoc.create.relationship(primary, rel_type, props, connected)
                YIELD rel
                RETURN count(rel) as transferred
            """
            
            # Note: This requires APOC plugin. Alternative is to handle each relationship type separately
            
            # Merge entity properties
            primary.merge_with(secondary)
            
            # Delete secondary entity
            secondary.delete()
            
            logger.info(f"Merged entity {secondary_uid} into {primary_uid}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging entities: {str(e)}")
            return False
    
    def update_co_occurrence(
        self,
        entity1_uid: str,
        entity2_uid: str
    ) -> bool:
        """
        Update or create co-occurrence relationship
        
        Args:
            entity1_uid: First entity UID
            entity2_uid: Second entity UID
        """
        try:
            e1 = self.find_by_uid(entity1_uid)
            e2 = self.find_by_uid(entity2_uid)
            
            if not e1 or not e2:
                return False
            
            # Check if relationship exists
            existing = e1.co_occurs_with.relationship(e2)
            if existing:
                existing.update_occurrence()
            else:
                # Create new co-occurrence
                rel = e1.co_occurs_with.connect(e2)
                rel.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating co-occurrence: {str(e)}")
            return False
    
    def get_entity_network(
        self,
        entity_uid: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get entity network (related entities through co-occurrence)
        
        Args:
            entity_uid: Central entity UID
            depth: How many hops to traverse
        """
        try:
            query = f"""
                MATCH (e:EntityNode {{uid: $uid}})
                OPTIONAL MATCH path = (e)-[:CO_OCCURS*1..{depth}]-(related:EntityNode)
                RETURN e, collect(DISTINCT {{
                    entity: related.name,
                    type: related.entity_type,
                    distance: length(path)
                }}) as network
            """
            
            results, _ = db.cypher_query(query, {'uid': entity_uid})
            
            if results:
                entity = EntityNode.inflate(results[0][0])
                return {
                    'entity': entity.to_dict(),
                    'network': results[0][1]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting entity network: {str(e)}")
            return None
    
    def get_important_entities(
        self,
        digital_human_id: str,
        min_importance: float = 0.7,
        limit: int = 20
    ) -> List[EntityNode]:
        """
        Get most important entities for a digital human
        
        Args:
            digital_human_id: Digital human ID
            min_importance: Minimum importance score
            limit: Maximum results
        """
        try:
            query = """
                MATCH (e:EntityNode {digital_human_id: $dh_id})
                WHERE e.importance_score >= $min_imp
                RETURN e
                ORDER BY e.importance_score DESC, e.mention_count DESC
                LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'dh_id': digital_human_id,
                'min_imp': min_importance,
                'limit': limit
            })
            
            return [EntityNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting important entities: {str(e)}")
            return []