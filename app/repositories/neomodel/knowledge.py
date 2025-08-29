"""
Knowledge Repository
Handles CRUD operations for Knowledge nodes
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from neomodel import db
from app.repositories.neomodel.base import NeomodelRepository as BaseRepository
from app.models.neomodel.knowledge import KnowledgeNode
from app.core.logger import logger


class KnowledgeRepository(BaseRepository):
    """Repository for Knowledge node operations"""
    
    def __init__(self):
        super().__init__(KnowledgeNode)
    
    def find_by_digital_human(
        self,
        digital_human_id: str,
        category: Optional[str] = None,
        validated_only: bool = False,
        limit: int = 100
    ) -> List[KnowledgeNode]:
        """
        Find knowledge for a specific digital human
        
        Args:
            digital_human_id: Digital human ID
            category: Optional category filter
            validated_only: Only return validated knowledge
            limit: Maximum number of results
        """
        try:
            query = "MATCH (k:KnowledgeNode {digital_human_id: $dh_id}) "
            params = {'dh_id': digital_human_id}
            
            conditions = []
            if category:
                conditions.append("k.category = $category")
                params['category'] = category
            
            if validated_only:
                conditions.append("k.validation_status = 'validated'")
            
            if conditions:
                query += "WHERE " + " AND ".join(conditions) + " "
            
            query += """
                RETURN k 
                ORDER BY k.importance DESC, k.learned_at DESC
                LIMIT $limit
            """
            params['limit'] = limit
            
            results, _ = db.cypher_query(query, params)
            return [KnowledgeNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error finding knowledge: {str(e)}")
            return []
    
    def find_related_knowledge(
        self,
        knowledge_uid: str,
        relationship_type: str = 'RELATED_TO',
        depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Find knowledge related to a specific piece of knowledge
        
        Args:
            knowledge_uid: Source knowledge UID
            relationship_type: Type of relationship to follow
            depth: How many hops to traverse
        """
        try:
            query = f"""
                MATCH (k:KnowledgeNode {{uid: $uid}})
                MATCH path = (k)-[:{relationship_type}*1..{depth}]-(related:KnowledgeNode)
                WHERE related.validation_status <> 'deprecated'
                RETURN DISTINCT related, length(path) as distance
                ORDER BY distance, related.importance DESC
                LIMIT 20
            """
            
            results, _ = db.cypher_query(query, {'uid': knowledge_uid})
            
            related = []
            for row in results:
                node = KnowledgeNode.inflate(row[0])
                related.append({
                    'knowledge': node.to_dict(),
                    'distance': row[1]
                })
            
            return related
            
        except Exception as e:
            logger.error(f"Error finding related knowledge: {str(e)}")
            return []
    
    def find_by_entities(
        self,
        entity_names: List[str],
        digital_human_id: str,
        limit: int = 50
    ) -> List[KnowledgeNode]:
        """
        Find knowledge that mentions specific entities
        
        Args:
            entity_names: List of entity names
            digital_human_id: Digital human context
            limit: Maximum results
        """
        try:
            query = """
                MATCH (k:KnowledgeNode {digital_human_id: $dh_id})-[:MENTIONS]->(e:EntityNode)
                WHERE e.name IN $entity_names
                RETURN DISTINCT k
                ORDER BY k.importance DESC
                LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'dh_id': digital_human_id,
                'entity_names': entity_names,
                'limit': limit
            })
            
            return [KnowledgeNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error finding knowledge by entities: {str(e)}")
            return []
    
    def find_contradictions(
        self,
        knowledge_uid: str
    ) -> List[Dict[str, Any]]:
        """
        Find knowledge that contradicts a specific piece of knowledge
        
        Args:
            knowledge_uid: Knowledge to check for contradictions
        """
        try:
            query = """
                MATCH (k:KnowledgeNode {uid: $uid})-[c:CONTRADICTS]-(other:KnowledgeNode)
                RETURN other, c.reason as reason, c.resolved as resolved
            """
            
            results, _ = db.cypher_query(query, {'uid': knowledge_uid})
            
            contradictions = []
            for row in results:
                node = KnowledgeNode.inflate(row[0])
                contradictions.append({
                    'knowledge': node.to_dict(),
                    'reason': row[1],
                    'resolved': row[2]
                })
            
            return contradictions
            
        except Exception as e:
            logger.error(f"Error finding contradictions: {str(e)}")
            return []
    
    def search_by_content(
        self,
        query_text: str,
        digital_human_id: str,
        limit: int = 20
    ) -> List[KnowledgeNode]:
        """
        Full-text search in knowledge content
        
        Args:
            query_text: Text to search for
            digital_human_id: Digital human context
            limit: Maximum results
        """
        try:
            # Use case-insensitive regex search
            query = """
                MATCH (k:KnowledgeNode {digital_human_id: $dh_id})
                WHERE k.content =~ $pattern OR k.summary =~ $pattern
                RETURN k
                ORDER BY k.importance DESC
                LIMIT $limit
            """
            
            # Create case-insensitive pattern
            pattern = f"(?i).*{query_text}.*"
            
            results, _ = db.cypher_query(query, {
                'dh_id': digital_human_id,
                'pattern': pattern,
                'limit': limit
            })
            
            return [KnowledgeNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}")
            return []
    
    def get_recent_knowledge(
        self,
        digital_human_id: str,
        hours: int = 24,
        limit: int = 50
    ) -> List[KnowledgeNode]:
        """
        Get recently learned knowledge
        
        Args:
            digital_human_id: Digital human ID
            hours: How many hours back to look
            limit: Maximum results
        """
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            query = """
                MATCH (k:KnowledgeNode {digital_human_id: $dh_id})
                WHERE k.learned_at > $cutoff
                RETURN k
                ORDER BY k.learned_at DESC
                LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'dh_id': digital_human_id,
                'cutoff': cutoff.isoformat(),
                'limit': limit
            })
            
            return [KnowledgeNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting recent knowledge: {str(e)}")
            return []
    
    def get_frequently_used(
        self,
        digital_human_id: str,
        min_usage: int = 5,
        limit: int = 20
    ) -> List[KnowledgeNode]:
        """
        Get frequently used knowledge
        
        Args:
            digital_human_id: Digital human ID
            min_usage: Minimum usage count
            limit: Maximum results
        """
        try:
            query = """
                MATCH (k:KnowledgeNode {digital_human_id: $dh_id})
                WHERE k.usage_count >= $min_usage
                RETURN k
                ORDER BY k.usage_count DESC
                LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'dh_id': digital_human_id,
                'min_usage': min_usage,
                'limit': limit
            })
            
            return [KnowledgeNode.inflate(row[0]) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting frequently used knowledge: {str(e)}")
            return []
    
    def update_contradiction(
        self,
        knowledge_uid1: str,
        knowledge_uid2: str,
        reason: str,
        resolution: Optional[str] = None
    ) -> bool:
        """
        Create or update a contradiction relationship
        
        Args:
            knowledge_uid1: First knowledge UID
            knowledge_uid2: Second knowledge UID
            reason: Reason for contradiction
            resolution: Optional resolution status
        """
        try:
            k1 = self.find_by_uid(knowledge_uid1)
            k2 = self.find_by_uid(knowledge_uid2)
            
            if not k1 or not k2:
                return False
            
            # Check if contradiction already exists
            existing = k1.contradicts.relationship(k2)
            if existing:
                existing.reason = reason
                if resolution:
                    existing.resolved = resolution
                existing.save()
            else:
                # Create new contradiction
                rel = k1.contradicts.connect(k2)
                rel.reason = reason
                if resolution:
                    rel.resolved = resolution
                rel.save()
            
            logger.info(f"Updated contradiction between {knowledge_uid1} and {knowledge_uid2}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating contradiction: {str(e)}")
            return False
    
    def get_knowledge_graph_stats(
        self,
        digital_human_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph
        
        Args:
            digital_human_id: Digital human ID
        """
        try:
            query = """
                MATCH (k:KnowledgeNode {digital_human_id: $dh_id})
                RETURN 
                    count(k) as total_knowledge,
                    avg(k.confidence) as avg_confidence,
                    avg(k.importance) as avg_importance,
                    sum(k.usage_count) as total_usage,
                    collect(DISTINCT k.category) as categories
            """
            
            results, _ = db.cypher_query(query, {'dh_id': digital_human_id})
            
            if results:
                row = results[0]
                return {
                    'total_knowledge': row[0],
                    'avg_confidence': row[1],
                    'avg_importance': row[2],
                    'total_usage': row[3],
                    'categories': row[4]
                }
            
            return {
                'total_knowledge': 0,
                'avg_confidence': 0,
                'avg_importance': 0,
                'total_usage': 0,
                'categories': []
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge stats: {str(e)}")
            return {}