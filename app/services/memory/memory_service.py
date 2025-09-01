"""
Memory Service
High-level service for managing digital human memories
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from app.core.memory.abstraction import IMemory
from app.core.memory.types import (
    MemoryDocument,
    MemoryType,
    MemorySource,
    MemoryStrength,
    RelationType
)
from app.services.memory.entity_extractor import EntityExtractor
from app.core.logger import logger


class MemoryService:
    """
    High-level service for memory operations
    Coordinates HybridMemory and EntityExtractor
    """
    
    def __init__(
        self,
        memory_impl: IMemory,
        entity_extractor: EntityExtractor,
        llm_service  # Required - no chat without LLM
    ):
        self.memory = memory_impl
        self.entity_extractor = entity_extractor
        self.llm = llm_service
        logger.info("✅ MemoryService initialized")
    
    async def remember_conversation(
        self,
        digital_human_id: int,
        user_message: str,
        assistant_response: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Process and store a conversation turn as memory
        
        Args:
            digital_human_id: The digital human involved
            user_message: What the user said
            assistant_response: What the assistant replied
            conversation_id: Optional conversation identifier
            session_id: Optional session identifier
        
        Returns:
            Memory ID if stored, None if not important enough
        """
        try:
            # Combine the conversation
            conversation_text = f"User: {user_message}\nAssistant: {assistant_response}"
            
            # Calculate importance using LLM
            importance = await self._calculate_memory_importance(conversation_text)
            
            # Only store if important enough
            if importance < 0.3:  # Threshold for storing
                logger.debug(f"Conversation not important enough to store (importance: {importance:.2f})")
                return None
            
            # Determine memory type using LLM or fallback
            memory_type = await self._determine_memory_type(conversation_text)
            
            # Create memory context
            # Initial strength is based on importance but can diverge over time
            initial_strength = self._calculate_initial_strength(importance)
            
            context = {
                'type': memory_type,
                'digital_human_id': str(digital_human_id),
                'source': MemorySource.CONVERSATION,
                'strength': initial_strength,
                'importance': importance
            }
            
            if conversation_id:
                context['conversation_id'] = conversation_id
            if session_id:
                context['session_id'] = session_id
            
            # Encode the memory
            memory_doc = await self.memory.encode(conversation_text, context)
            
            # Store the memory
            memory_id = await self.memory.store(memory_doc)
            
            # Extract and store entities
            entities = await self.entity_extractor.extract_entities(conversation_text)
            if entities:
                await self.entity_extractor.store_entities(
                    entities,
                    memory_id,
                    str(digital_human_id)
                )
            
            # Find and create associations with recent memories
            await self._create_memory_associations(memory_id, str(digital_human_id), conversation_text)
            
            logger.info(f"Stored conversation memory {memory_id} with importance {importance:.2f}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to remember conversation: {str(e)}")
            return None
    
    async def _calculate_memory_importance(self, conversation_text: str) -> float:
        """
        Calculate the importance of a conversation for memory storage using LLM
        
        Args:
            conversation_text: The full conversation text
        
        Returns:
            Importance score from 0.0 to 1.0
        """
        try:
            # Use LLM to assess importance
            prompt = """Analyze this conversation and rate its importance for long-term memory storage.

Consider these factors:
1. Personal information about the user (names, preferences, facts, background)
2. Important questions or requests
3. Learning moments or new knowledge shared
4. Emotional significance
5. Future relevance (will this be useful to remember later?)
6. Unique or specific information (vs generic chat)

Conversation:
{text}

Rate the importance on a scale of 0.0 to 1.0 where:
- 0.0-0.2: Trivial small talk, no valuable information
- 0.3-0.5: Some useful context but not critical
- 0.6-0.8: Important information worth remembering
- 0.9-1.0: Critical information that must be remembered

Return ONLY a number between 0.0 and 1.0, nothing else."""
            
            formatted_prompt = prompt.format(text=conversation_text[:1500])  # Limit length
            
            # Get LLM response
            response = await self.llm.chat_sync(
                formatted_prompt,
                thread_id="importance_calculation",
                digital_human_config={
                    'temperature': 0.3,  # Low temperature for consistent scoring
                    'max_tokens': 10
                }
            )
            
            # Parse the response to extract the number
            import re
            match = re.search(r'(\d*\.?\d+)', response.strip())
            if match:
                importance = float(match.group(1))
                # Ensure it's within bounds
                importance = max(0.0, min(1.0, importance))
                logger.debug(f"LLM calculated importance: {importance}")
                return importance
            else:
                logger.warning(f"Could not parse importance from LLM response: {response}")
                return 0.5  # Default middle importance if parsing fails
                
        except Exception as e:
            logger.error(f"Failed to calculate importance with LLM: {str(e)}")
            raise  # Let the error propagate - no chat without LLM anyway
    
    async def _determine_memory_type(self, text: str) -> MemoryType:
        """
        Determine the type of memory based on content using LLM
        """
        try:
            prompt = """Classify this conversation into the most appropriate memory type.

Memory Types:
- EPISODIC: Personal experiences, events, specific moments in time
- SEMANTIC: Facts, concepts, general knowledge
- PROCEDURAL: Skills, how-to knowledge, steps to accomplish tasks
- EMOTIONAL: Feelings, emotional states, personal reactions
- SHORT_TERM: Temporary context, current task information
- LONG_TERM: Important information to preserve permanently
- WORKING: Active task context, current problem-solving
- SENSORY: Descriptions of sensations, perceptions

Conversation:
{text}

Return ONLY one word: EPISODIC, SEMANTIC, PROCEDURAL, EMOTIONAL, SHORT_TERM, LONG_TERM, WORKING, or SENSORY"""

            formatted_prompt = prompt.format(text=text[:1000])
            
            response = await self.llm.chat_sync(
                formatted_prompt,
                thread_id="memory_type_classification",
                digital_human_config={
                    'temperature': 0.2,  # Low temperature for consistent classification
                    'max_tokens': 10
                }
            )
            
            # Parse response and map to MemoryType enum
            response_clean = response.strip().upper()
            
            # Map response to enum
            type_mapping = {
                'EPISODIC': MemoryType.EPISODIC,
                'SEMANTIC': MemoryType.SEMANTIC,
                'PROCEDURAL': MemoryType.PROCEDURAL,
                'EMOTIONAL': MemoryType.EMOTIONAL,
                'SHORT_TERM': MemoryType.SHORT_TERM,
                'LONG_TERM': MemoryType.LONG_TERM,
                'WORKING': MemoryType.WORKING,
                'SENSORY': MemoryType.SENSORY
            }
            
            memory_type = type_mapping.get(response_clean, MemoryType.SHORT_TERM)
            logger.debug(f"LLM classified memory as: {memory_type.value}")
            return memory_type
            
        except Exception as e:
            logger.error(f"Failed to determine memory type: {str(e)}")
            return MemoryType.SHORT_TERM  # Safe default if classification fails
    
    def _calculate_initial_strength(self, importance: float) -> float:
        """
        Calculate initial memory strength based on importance
        
        Strength starts correlated with importance but will diverge over time:
        - High importance memories start moderately strong (not maximum)
        - This allows room for growth through access
        - Very low importance memories start very weak
        """
        if importance >= 0.8:
            # Very important: start at 70% strength
            return 0.7
        elif importance >= 0.6:
            # Important: start at 60% strength
            return 0.6
        elif importance >= 0.4:
            # Moderate: start at 50% strength
            return 0.5
        elif importance >= 0.2:
            # Low importance: start at 30% strength
            return 0.3
        else:
            # Trivial: start very weak
            return 0.1
    
    async def recall_relevant_memories(
        self,
        query: str,
        digital_human_id: int,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories relevant to a query
        
        Args:
            query: The search query
            digital_human_id: The digital human context
            memory_types: Optional filter for memory types
            limit: Maximum number of memories to return
        
        Returns:
            List of relevant memories with their content and metadata
        """
        try:
            filters = {
                'digital_human_id': str(digital_human_id)
            }
            
            if memory_types:
                filters['memory_types'] = memory_types
            
            # Retrieve memories using hybrid search
            memories = await self.memory.retrieve(query, limit=limit, filters=filters)
            
            # Enrich memories with entity context
            enriched_memories = []
            for memory in memories:
                # Extract entities mentioned in this memory
                memory_id = memory.get('memory_id')
                if memory_id:
                    # Get associated entities from graph
                    entities = await self._get_memory_entities(memory_id)
                    memory['entities'] = entities
                
                enriched_memories.append(memory)
            
            return enriched_memories
            
        except Exception as e:
            logger.error(f"Failed to recall memories: {str(e)}")
            return []
    
    async def _get_memory_entities(self, memory_id: str) -> List[Dict[str, Any]]:
        """Get entities mentioned in a memory"""
        try:
            # This would query Neo4j for entities linked to this memory
            # Simplified for now
            return []
        except Exception as e:
            logger.error(f"Failed to get memory entities: {str(e)}")
            return []
    
    async def _create_memory_associations(self, memory_id: str, digital_human_id: str, current_memory_content: str = None):
        """
        Create intelligent associations between related memories using LLM
        """
        try:
            # Get recent memories to check for associations
            recent_memories = await self.memory.retrieve(
                query="",  # Empty query to get recent
                limit=5,  # Fewer memories to analyze relationships
                filters={'digital_human_id': digital_human_id}
            )
            
            for recent_memory in recent_memories:
                if recent_memory.get('memory_id') != memory_id:
                    # Use LLM to determine relationship type
                    relation_type = await self._determine_memory_relationship(
                        memory1_content=recent_memory.get('content', recent_memory.get('summary', '')),
                        memory2_content=current_memory_content or ""
                    )
                    
                    if relation_type:
                        await self.memory.associate(
                            memory_id,
                            recent_memory['memory_id'],
                            relation_type,
                            strength=0.6  # Moderate initial strength
                        )
                        logger.debug(f"Created {relation_type} relationship between memories")
            
        except Exception as e:
            logger.error(f"Failed to create memory associations: {str(e)}")
    
    async def _determine_memory_relationship(self, memory1_content: str, memory2_content: str) -> Optional[str]:
        """
        Use LLM to determine the relationship type between two memories
        """
        try:
            prompt = """Analyze the relationship between these two memories and classify it.

Memory 1: {mem1}
Memory 2: {mem2}

Relationship Types:
- SIMILAR: Memories about related topics or concepts
- CAUSAL: One memory describes a cause/effect of the other
- TEMPORAL: Memories that occurred in sequence (use only if explicitly time-related)
- HIERARCHICAL: One memory is a category/subset of the other
- CONTRADICTORY: Memories contain conflicting information
- COMPLEMENTARY: Memories complete or enhance each other
- NONE: No clear relationship

Return ONLY one word: SIMILAR, CAUSAL, TEMPORAL, HIERARCHICAL, CONTRADICTORY, COMPLEMENTARY, or NONE"""

            formatted_prompt = prompt.format(
                mem1=memory1_content[:500],
                mem2=memory2_content[:500]
            )
            
            response = await self.llm.chat_sync(
                formatted_prompt,
                thread_id="relationship_classification",
                digital_human_config={
                    'temperature': 0.3,
                    'max_tokens': 10
                }
            )
            
            response_clean = response.strip().upper()
            
            # Validate response
            valid_types = ['SIMILAR', 'CAUSAL', 'TEMPORAL', 'HIERARCHICAL', 
                          'CONTRADICTORY', 'COMPLEMENTARY', 'NONE']
            
            if response_clean in valid_types:
                if response_clean == 'NONE':
                    return None  # No relationship
                return response_clean.lower()  # Return lowercase for enum
            else:
                logger.warning(f"Invalid relationship type from LLM: {response_clean}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to determine relationship: {str(e)}")
            return None
    
    async def consolidate_important_memories(self, digital_human_id: int):
        """
        Periodically consolidate ALL memories based on importance and access patterns
        """
        try:
            # Get ALL memories for this digital human
            # Use the get_all_memories method to get all memories for maintenance
            memories = await self.memory.get_all_memories(str(digital_human_id))
            
            consolidated_count = 0
            decayed_count = 0
            
            for memory in memories:
                memory_id = memory.get('memory_id')
                importance = memory.get('importance', 0.5)
                access_count = memory.get('access_count', 0)
                
                # Different strategies based on importance and usage
                if importance > 0.7 and access_count > 0:
                    # Important AND accessed: strengthen
                    await self.memory.consolidate(memory_id, factor=1.1)
                    consolidated_count += 1
                elif importance > 0.7 and access_count == 0:
                    # Important but never accessed: mild decay
                    await self.memory.decay(memory_id, rate=0.05)
                    decayed_count += 1
                elif importance < 0.3 and access_count < 2:
                    # Unimportant and rarely accessed: stronger decay
                    await self.memory.decay(memory_id, rate=0.3)
                    decayed_count += 1
                elif importance < 0.3 and access_count > 5:
                    # Unimportant but frequently accessed: mild strengthen
                    # (habit memories, like common phrases)
                    await self.memory.consolidate(memory_id, factor=1.02)
                    consolidated_count += 1
            
            logger.info(f"Memory maintenance complete for digital human {digital_human_id}: "
                       f"{consolidated_count} consolidated, {decayed_count} decayed, "
                       f"{len(memories)} total processed")
            
        except Exception as e:
            logger.error(f"Failed to consolidate memories: {str(e)}")
    
    async def get_memory_statistics(self, digital_human_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics about stored memories
        
        Returns stats including:
        - 总共的记忆节点 (total memory nodes)
        - 总共的关系连接 (total relationships)
        - 文档片段 (document fragments)
        - 向量覆盖百分比 (vector coverage percentage)
        - 不同记忆类型的数量 (memory type counts)
        - Recent memories description
        """
        try:
            dh_id = str(digital_human_id)
            
            # Query 1: Total memories and memory types
            memory_stats_query = """
            MATCH (m:Memory {digital_human_id: $dh_id})
            RETURN 
                count(m) as total_memories,
                m.type as memory_type,
                count(m.type) as type_count
            ORDER BY type_count DESC
            """
            memory_results = await self.memory.execute_query(
                memory_stats_query, {'dh_id': dh_id}
            )
            
            # Process memory type counts
            total_memories = 0
            memory_types = {}
            for result in memory_results:
                total_memories += result['type_count']
                memory_types[result['memory_type']] = result['type_count']
            
            # Query 2: Total relationships
            relationship_query = """
            MATCH (m1:Memory {digital_human_id: $dh_id})-[r]-(m2:Memory)
            RETURN count(DISTINCT r) as total_relationships
            """
            rel_results = await self.memory.execute_query(
                relationship_query, {'dh_id': dh_id}
            )
            total_relationships = rel_results[0]['total_relationships'] if rel_results else 0
            
            # Query 3: Total entities
            entity_query = """
            MATCH (e:Entity {digital_human_id: $dh_id})
            RETURN count(e) as total_entities
            """
            entity_results = await self.memory.execute_query(
                entity_query, {'dh_id': dh_id}
            )
            total_entities = entity_results[0]['total_entities'] if entity_results else 0
            
            # Query 4: Document fragments (memories with content)
            fragments_query = """
            MATCH (m:Memory {digital_human_id: $dh_id})
            WHERE m.summary IS NOT NULL
            RETURN count(m) as document_fragments
            """
            fragment_results = await self.memory.execute_query(
                fragments_query, {'dh_id': dh_id}
            )
            document_fragments = fragment_results[0]['document_fragments'] if fragment_results else 0
            
            # Query 5: Vector coverage (memories with embeddings in Chroma)
            # Check how many memories have chroma_doc_id (indicating they're in Chroma)
            vector_query = """
            MATCH (m:Memory {digital_human_id: $dh_id})
            WITH count(m) as total,
                 sum(CASE WHEN m.chroma_doc_id IS NOT NULL THEN 1 ELSE 0 END) as with_vectors
            RETURN total, with_vectors,
                   CASE WHEN total > 0 THEN (with_vectors * 100.0 / total) ELSE 0 END as coverage_percent
            """
            vector_results = await self.memory.execute_query(
                vector_query, {'dh_id': dh_id}
            )
            vector_coverage = vector_results[0]['coverage_percent'] if vector_results else 0
            
            # Query 6: Recent memories with summaries
            recent_query = """
            MATCH (m:Memory {digital_human_id: $dh_id})
            WHERE m.summary IS NOT NULL
            RETURN m.memory_id as id, 
                   m.summary as summary,
                   m.importance as importance,
                   m.created_at as created_at
            ORDER BY m.created_at DESC
            LIMIT 5
            """
            recent_results = await self.memory.execute_query(
                recent_query, {'dh_id': dh_id}
            )
            
            recent_memories = [
                {
                    'id': r['id'],
                    'summary': r['summary'][:100] + '...' if len(r.get('summary', '')) > 100 else r.get('summary', ''),
                    'importance': r.get('importance', 0),
                    'created_at': r.get('created_at', '')
                }
                for r in recent_results
            ]
            
            # Query 7: Top entities by frequency
            top_entities_query = """
            MATCH (e:Entity {digital_human_id: $dh_id})
            RETURN e.name as name, e.type as type, e.frequency as frequency
            ORDER BY e.frequency DESC
            LIMIT 10
            """
            entity_results = await self.memory.execute_query(
                top_entities_query, {'dh_id': dh_id}
            )
            
            top_entities = [
                {'name': e['name'], 'type': e['type'], 'frequency': e.get('frequency', 0)}
                for e in entity_results
            ]
            
            # Compile all statistics
            stats = {
                # Core metrics
                'total_memory_nodes': total_memories,  # 总共的记忆节点
                'total_relationships': total_relationships,  # 总共的关系连接
                'document_fragments': document_fragments,  # 文档片段
                'vector_coverage_percent': round(vector_coverage, 2),  # 向量覆盖百分比
                
                # Memory type breakdown
                'memory_types': memory_types,  # 不同记忆类型的数量
                
                # Entity statistics
                'total_entities': total_entities,
                'top_entities': top_entities,
                
                # Recent activity
                'recent_memories': recent_memories
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get memory statistics: {str(e)}")
            return {
                'total_memory_nodes': 0,
                'total_relationships': 0,
                'document_fragments': 0,
                'vector_coverage_percent': 0,
                'memory_types': {},
                'total_entities': 0,
                'top_entities': [],
                'recent_memories': []
            }