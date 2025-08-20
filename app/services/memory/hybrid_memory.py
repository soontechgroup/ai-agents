"""
Hybrid Memory Implementation
Combines Chroma for vector search with Neo4j for relationship management
"""

from typing import Any, List, Dict, Optional
from datetime import datetime
import uuid
import json
from app.core.memory.abstraction import IMemory
from app.core.memory.types import (
    MemoryDocument,
    MemoryType,
    MemoryStrength,
    MemoryImportance,
    MemorySource,
    RelationType,
    MemoryMetadata
)
from app.services.chroma_service import ChromaService
from app.services.embedding_service import EmbeddingService
from app.repositories.graph import GraphRepository
from app.schemas.chroma import (
    ChromaDocumentBatch, 
    ChromaDocumentInput, 
    ChromaQueryRequest,
    ChromaCreateCollectionRequest
)
from app.core.logger import logger


class HybridMemory(IMemory):
    """
    Concrete implementation of IMemory using Chroma for vectors and Neo4j for relationships
    """
    
    def __init__(
        self,
        chroma_service: ChromaService,
        graph_repo: GraphRepository,
        embedding_service: EmbeddingService
    ):
        self.chroma = chroma_service
        self.graph = graph_repo
        self.embeddings = embedding_service
        logger.info("✅ HybridMemory initialized with Chroma and Neo4j")
    
    def _get_collection_name(self, digital_human_id: str) -> str:
        """Get the Chroma collection name for a digital human"""
        return f"dh_{digital_human_id}_memories"
    
    async def encode(self, content: Any, context: Optional[Dict] = None) -> Dict:
        """
        Encode content into a MemoryDocument with embedding
        """
        try:
            text_content = str(content)
            context = context or {}
            
            # Generate embedding for the content
            embedding = self.embeddings.generate_query_embedding(text_content)
            
            # Extract keywords (simple approach - can be enhanced with NLP)
            keywords = [word.lower() for word in text_content.split() 
                       if len(word) > 4 and word.isalnum()][:10]
            
            # Build metadata
            metadata: MemoryMetadata = {
                'digital_human_id': str(context.get('digital_human_id', '')),
                'source': context.get('source', MemorySource.CONVERSATION),
                'timestamp': datetime.now(),
                'confidence': context.get('confidence', 0.8),
                'tags': context.get('tags', []),
                'context': context.get('extra_context', {})
            }
            
            # Add optional metadata fields
            if 'user_id' in context:
                metadata['user_id'] = str(context['user_id'])
            if 'session_id' in context:
                metadata['session_id'] = str(context['session_id'])
            if 'conversation_id' in context:
                metadata['conversation_id'] = str(context['conversation_id'])
            
            # Create MemoryDocument
            memory_doc: MemoryDocument = {
                'memory_id': f"mem_{uuid.uuid4()}",
                'memory_type': context.get('type', MemoryType.SHORT_TERM),
                'content': text_content,
                'summary': text_content[:200] if len(text_content) > 200 else text_content,
                'keywords': keywords,
                'entities': [],  # Will be populated by entity extractor
                'embedding': embedding,
                'strength': context.get('strength', MemoryStrength.MEDIUM),
                'importance': context.get('importance', 0.5),  # Use importance from context
                'access_count': 0,
                'last_accessed': datetime.now(),
                'decay_rate': context.get('decay_rate', 0.1),
                'metadata': metadata,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'associations': []
            }
            
            logger.debug(f"Encoded memory: {memory_doc['memory_id']} with {len(embedding)} dimensions")
            return memory_doc
            
        except Exception as e:
            logger.error(f"Failed to encode memory: {str(e)}")
            raise
    
    async def store(self, memory: Dict) -> str:
        """
        Store memory in both Chroma (vectors) and Neo4j (metadata/relationships)
        """
        try:
            memory_id = memory['memory_id']
            digital_human_id = memory['metadata'].get('digital_human_id', 'unknown')
            
            # Ensure collection exists in Chroma
            collection_name = self._get_collection_name(digital_human_id)
            await self._ensure_collection_exists(collection_name)
            
            # Store in Chroma for vector search
            chroma_metadata = {
                'memory_id': memory_id,
                'memory_type': memory['memory_type'].value if isinstance(memory['memory_type'], MemoryType) else memory['memory_type'],
                'importance': float(memory['importance']),
                'digital_human_id': digital_human_id,
                'created_at': memory['created_at'].isoformat()
            }
            
            # Store in Chroma and get the document ID
            chroma_result = self.chroma.add_documents(
                ChromaDocumentBatch(
                    collection_name=collection_name,
                    documents=[ChromaDocumentInput(
                        content=memory['content'],
                        metadata=chroma_metadata
                    )]
                )
            )
            
            # Get the Chroma document ID for later deletion
            chroma_doc_id = None
            if chroma_result and chroma_result.document_ids:
                chroma_doc_id = chroma_result.document_ids[0]
            
            # Store in Neo4j for relationships (including Chroma doc ID)
            neo4j_properties = {
                'memory_id': memory_id,
                'chroma_doc_id': chroma_doc_id,  # Store Chroma document ID for deletion
                'type': memory['memory_type'].value if isinstance(memory['memory_type'], MemoryType) else memory['memory_type'],
                'strength': float(memory['strength']),
                'importance': float(memory['importance']),
                'access_count': memory['access_count'],
                'decay_rate': memory['decay_rate'],
                'digital_human_id': digital_human_id,
                'created_at': memory['created_at'].isoformat(),
                'summary': memory.get('summary', '')[:500]  # Store summary for quick access
            }
            
            node = self.graph.nodes.create(
                label='Memory',
                properties=neo4j_properties
            )
            
            logger.info(f"✅ Stored memory {memory_id} in both Chroma and Neo4j")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {str(e)}")
            raise
    
    async def retrieve(self, query: Any, limit: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Hybrid retrieval: Vector search → Entity discovery → Graph expansion
        """
        try:
            filters = filters or {}
            digital_human_id = filters.get('digital_human_id', 'unknown')
            collection_name = self._get_collection_name(digital_human_id)
            
            # Step 1: Vector similarity search in Chroma for initial memories
            query_text = str(query)
            
            # Build Chroma filter
            chroma_filter = {}
            if 'memory_types' in filters:
                memory_types = filters['memory_types']
                if memory_types:
                    type_values = [t.value if isinstance(t, MemoryType) else t for t in memory_types]
                    chroma_filter['memory_type'] = {"$in": type_values}
            
            # Query Chroma for similar memories
            chroma_results = self.chroma.query_documents(
                ChromaQueryRequest(
                    collection_name=collection_name,
                    query_text=query_text,
                    n_results=limit,  # Get initial set
                    where=chroma_filter if chroma_filter else None
                )
            )
            
            # Step 2: Extract entities from retrieved memories
            entity_ids = set()
            memory_ids = []
            
            for doc in chroma_results.documents:
                memory_id = doc.metadata.get('memory_id')
                if memory_id:
                    memory_ids.append(memory_id)
                    
                    # Find entities mentioned in this memory
                    entities = await self._get_entities_from_memory(memory_id)
                    entity_ids.update(entities)
            
            # Step 3: Graph expansion - find more memories through entity relationships
            expanded_memory_ids = set(memory_ids)  # Start with initial memories
            
            if entity_ids:
                # Find memories that mention the same entities
                related_memories = await self._get_memories_from_entities(
                    list(entity_ids), 
                    digital_human_id,
                    exclude_ids=memory_ids,
                    limit=limit
                )
                expanded_memory_ids.update(related_memories)
                
                # Find related entities through graph relationships
                related_entities = await self._get_related_entities(
                    list(entity_ids),
                    digital_human_id
                )
                
                # Find memories mentioning related entities
                if related_entities:
                    additional_memories = await self._get_memories_from_entities(
                        related_entities,
                        digital_human_id,
                        exclude_ids=list(expanded_memory_ids),
                        limit=limit // 2  # Less from indirect relationships
                    )
                    expanded_memory_ids.update(additional_memories)
            
            # Step 4: Retrieve full memory content and rank by relevance
            memories = []
            for i, doc in enumerate(chroma_results.documents):
                memory_id = doc.metadata.get('memory_id')
                if memory_id:
                    memory_doc = {
                        'memory_id': memory_id,
                        'content': doc.content,
                        'memory_type': doc.metadata.get('memory_type'),
                        'importance': doc.metadata.get('importance', 0.5),
                        'distance': doc.distance,
                        'retrieval_rank': i + 1,
                        'source': 'direct_search'
                    }
                    memories.append(memory_doc)
            
            # Add expanded memories (with lower rank)
            for memory_id in expanded_memory_ids:
                if memory_id not in memory_ids:  # Don't duplicate
                    memory_node = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id)
                    if memory_node:
                        memories.append({
                            'memory_id': memory_id,
                            'summary': memory_node['properties'].get('summary', ''),
                            'memory_type': memory_node['properties'].get('type'),
                            'importance': memory_node['properties'].get('importance', 0.3),
                            'source': 'graph_expansion'
                        })
            
            # Step 5: Strengthen accessed memories (consolidation through use)
            # Each access makes the memory slightly stronger (easier to recall next time)
            for memory in memories[:limit]:  # Only update top results
                await self.consolidate(memory['memory_id'], factor=1.05)  # 5% strength increase per access
            
            logger.info(f"Retrieved {len(memories)} memories ({len(memory_ids)} direct, {len(expanded_memory_ids) - len(memory_ids)} expanded)")
            return memories[:limit * 2]  # Return more than requested for re-ranking
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {str(e)}")
            return []
    
    async def _get_entities_from_memory(self, memory_id: str) -> List[str]:
        """Get entity IDs mentioned in a memory"""
        try:
            query = """
            MATCH (m:Memory {memory_id: $memory_id})-[:MENTIONS]->(e:Entity)
            RETURN collect(DISTINCT id(e)) as entity_ids
            """
            results = self.graph.execute_cypher(query, {'memory_id': memory_id})
            return results[0]['entity_ids'] if results else []
        except Exception as e:
            logger.error(f"Failed to get entities from memory: {str(e)}")
            return []
    
    async def _get_memories_from_entities(
        self, 
        entity_ids: List[str], 
        digital_human_id: str,
        exclude_ids: List[str] = None,
        limit: int = 10
    ) -> List[str]:
        """Get memories that mention specific entities"""
        try:
            exclude_ids = exclude_ids or []
            query = """
            MATCH (e:Entity)<-[:MENTIONS]-(m:Memory)
            WHERE id(e) IN $entity_ids 
            AND m.digital_human_id = $dh_id
            AND NOT m.memory_id IN $exclude_ids
            RETURN DISTINCT m.memory_id as memory_id
            ORDER BY m.importance DESC
            LIMIT $limit
            """
            results = self.graph.execute_cypher(query, {
                'entity_ids': entity_ids,
                'dh_id': digital_human_id,
                'exclude_ids': exclude_ids,
                'limit': limit
            })
            return [r['memory_id'] for r in results]
        except Exception as e:
            logger.error(f"Failed to get memories from entities: {str(e)}")
            return []
    
    async def _get_related_entities(
        self,
        entity_ids: List[str],
        digital_human_id: str,
        max_entities: int = 10
    ) -> List[str]:
        """Get related entities through graph relationships"""
        try:
            query = """
            MATCH (e1:Entity)-[:CO_OCCURS]-(e2:Entity)
            WHERE id(e1) IN $entity_ids
            AND e2.digital_human_id = $dh_id
            AND NOT id(e2) IN $entity_ids
            RETURN DISTINCT id(e2) as entity_id
            LIMIT $limit
            """
            results = self.graph.execute_cypher(query, {
                'entity_ids': entity_ids,
                'dh_id': digital_human_id,
                'limit': max_entities
            })
            return [r['entity_id'] for r in results]
        except Exception as e:
            logger.error(f"Failed to get related entities: {str(e)}")
            return []
    
    async def _get_related_memories(self, memory_id: str, limit: int = 3) -> List[Dict]:
        """Get related memories through graph traversal"""
        try:
            query = """
            MATCH (m:Memory {memory_id: $memory_id})-[r]-(related:Memory)
            RETURN related.memory_id as id, related.summary as summary, type(r) as relation
            ORDER BY related.importance DESC
            LIMIT $limit
            """
            
            results = self.graph.execute_cypher(query, {
                'memory_id': memory_id,
                'limit': limit
            })
            
            return [{'id': r['id'], 'summary': r['summary'], 'relation': r['relation']} 
                   for r in results]
            
        except Exception as e:
            logger.error(f"Failed to get related memories: {str(e)}")
            return []
    
    async def update(self, memory_id: str, updates: Dict) -> bool:
        """Update memory properties"""
        try:
            # Update in Neo4j
            memory_node = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id)
            if memory_node:
                # Update only allowed fields
                allowed_updates = {}
                for key in ['importance', 'strength', 'access_count', 'summary']:
                    if key in updates:
                        allowed_updates[key] = updates[key]
                
                if allowed_updates:
                    allowed_updates['updated_at'] = datetime.now().isoformat()
                    self.graph.nodes.update(memory_node['id'], allowed_updates)
                    logger.debug(f"Updated memory {memory_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update memory: {str(e)}")
            return False
    
    async def consolidate(self, memory_id: str, factor: float = 1.2) -> bool:
        """Strengthen memory based on access"""
        try:
            memory_node = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id)
            if memory_node:
                current_strength = memory_node['properties'].get('strength', 0.5)
                new_strength = min(current_strength * factor, 1.0)
                
                access_count = memory_node['properties'].get('access_count', 0)
                
                self.graph.nodes.update(memory_node['id'], {
                    'strength': new_strength,
                    'access_count': access_count + 1,
                    'last_accessed': datetime.now().isoformat()
                })
                
                logger.debug(f"Consolidated memory {memory_id}: strength {current_strength:.2f} -> {new_strength:.2f}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to consolidate memory: {str(e)}")
            return False
    
    async def decay(self, memory_id: str, rate: float = 0.1) -> bool:
        """Weaken memory over time"""
        try:
            memory_node = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id)
            if memory_node:
                current_strength = memory_node['properties'].get('strength', 0.5)
                new_strength = max(current_strength * (1 - rate), 0.1)  # Keep minimum strength
                
                self.graph.nodes.update(memory_node['id'], {
                    'strength': new_strength,
                    'updated_at': datetime.now().isoformat()
                })
                
                logger.debug(f"Decayed memory {memory_id}: strength {current_strength:.2f} -> {new_strength:.2f}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to decay memory: {str(e)}")
            return False
    
    async def forget(self, memory_id: str) -> bool:
        """Delete memory from both stores"""
        try:
            # First get the memory node to retrieve Chroma doc ID
            memory_node = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id)
            if not memory_node:
                logger.warning(f"Memory {memory_id} not found")
                return False
            
            # Get the Chroma document ID and digital human ID
            chroma_doc_id = memory_node['properties'].get('chroma_doc_id')
            digital_human_id = memory_node['properties'].get('digital_human_id', 'unknown')
            
            # Delete from Chroma if we have the document ID
            if chroma_doc_id:
                try:
                    collection_name = self._get_collection_name(digital_human_id)
                    self.chroma.delete_documents(
                        collection_name=collection_name,
                        document_ids=[chroma_doc_id]
                    )
                    logger.debug(f"Deleted from Chroma: {chroma_doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete from Chroma: {str(e)}")
            
            # Delete from Neo4j (this also deletes relationships)
            self.graph.nodes.delete(memory_node['id'])
            
            logger.info(f"Deleted memory {memory_id} from both stores")
            return True
            
        except Exception as e:
            logger.error(f"Failed to forget memory: {str(e)}")
            return False
    
    async def associate(self, memory_id1: str, memory_id2: str, relation_type: str, strength: float = 0.5) -> bool:
        """Create association between memories"""
        try:
            # Validate relation type
            valid_relations = [r.value for r in RelationType]
            if relation_type not in valid_relations:
                logger.warning(f"Invalid relation type: {relation_type}")
                return False
            
            # Find both memories in Neo4j
            memory1 = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id1)
            memory2 = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id2)
            
            if memory1 and memory2:
                # Create relationship
                self.graph.relationships.create(
                    from_id=memory1['id'],
                    to_id=memory2['id'],
                    type=relation_type.upper(),
                    properties={
                        'strength': strength,
                        'created_at': datetime.now().isoformat()
                    }
                )
                
                logger.info(f"Created {relation_type} association between {memory_id1} and {memory_id2}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to create association: {str(e)}")
            return False
    
    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a Cypher query (for statistics and maintenance)
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query results
        """
        try:
            return self.graph.execute_cypher(query, parameters or {})
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            return []
    
    async def get_all_memories(self, digital_human_id: str, include_weak: bool = False) -> List[Dict]:
        """
        Get all memories for maintenance/consolidation (not for search)
        
        Args:
            digital_human_id: The digital human to get memories for
            include_weak: Whether to include very weak memories (strength < 0.1)
        
        Returns:
            List of all memory records with their properties
        """
        try:
            query = """
            MATCH (m:Memory {digital_human_id: $dh_id})
            """ + ("WHERE m.strength >= 0.1" if not include_weak else "") + """
            RETURN m.memory_id as memory_id,
                   m.importance as importance,
                   m.strength as strength,
                   m.access_count as access_count,
                   m.type as memory_type,
                   m.created_at as created_at,
                   m.last_accessed as last_accessed
            ORDER BY m.importance DESC
            """
            
            results = self.graph.execute_cypher(query, {'dh_id': digital_human_id})
            return results
            
        except Exception as e:
            logger.error(f"Failed to get all memories: {str(e)}")
            return []
    
    async def get_associations(self, memory_id: str, relation_type: Optional[str] = None) -> List[Dict]:
        """Get all associations for a memory"""
        try:
            if relation_type:
                query = """
                MATCH (m:Memory {memory_id: $memory_id})-[r:%s]-(related:Memory)
                RETURN related.memory_id as id, related.summary as summary, 
                       type(r) as relation, r.strength as strength
                """ % relation_type.upper()
            else:
                query = """
                MATCH (m:Memory {memory_id: $memory_id})-[r]-(related:Memory)
                RETURN related.memory_id as id, related.summary as summary, 
                       type(r) as relation, r.strength as strength
                """
            
            results = self.graph.execute_cypher(query, {'memory_id': memory_id})
            
            associations = []
            for r in results:
                associations.append({
                    'memory_id': r['id'],
                    'summary': r['summary'],
                    'relation_type': r['relation'],
                    'strength': r.get('strength', 0.5)
                })
            
            return associations
            
        except Exception as e:
            logger.error(f"Failed to get associations: {str(e)}")
            return []
    
    async def _ensure_collection_exists(self, collection_name: str):
        """Ensure Chroma collection exists"""
        try:
            # Try to get collection info
            try:
                self.chroma.get_collection_info(collection_name)
            except Exception:
                # Collection doesn't exist, create it
                self.chroma.create_collection(
                    ChromaCreateCollectionRequest(
                        collection_name=collection_name,
                        metadata={'type': 'memory', 'created_at': datetime.now().isoformat()}
                    )
                )
                logger.info(f"Created Chroma collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {str(e)}")