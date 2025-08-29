"""
Entity Extraction Service
Extracts entities from text using LLM and manages them in Neo4j
"""

from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime
from app.services.graph_service import GraphService
from app.services.langgraph_service import LangGraphService
from app.core.logger import logger


class EntityExtractor:
    """
    Extracts entities from text and manages them in the graph database
    """
    
    def __init__(self, graph_service: GraphService, llm_service: LangGraphService):
        self.graph = graph_service
        self.llm = llm_service
        logger.info("✅ EntityExtractor initialized")
    
    async def extract_entities(self, text: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Extract entities from text using LLM
        
        Args:
            text: The text to extract entities from
            context: Optional context (digital_human_id, etc.)
        
        Returns:
            List of entity dictionaries with name, type, and context
        """
        try:
            # Prepare the prompt for entity extraction
            prompt = """Extract all important entities from the following text. 
Include people, places, organizations, concepts, technologies, events, and any other notable items.

Text: {text}

Return ONLY a valid JSON array with this exact format:
[
    {{"name": "entity name", "type": "person|place|organization|concept|technology|event|other", "context": "brief description"}}
]

Rules:
- Extract actual entities mentioned, not generic terms
- Include proper nouns and specific concepts
- Keep entity names concise (1-3 words)
- Provide context that explains the entity's relevance
- If no entities found, return empty array []

Examples:
Text: "I work at Google as a Python developer"
Output: [{{"name": "Google", "type": "organization", "context": "employer"}}, {{"name": "Python", "type": "technology", "context": "programming language used at work"}}]

Now extract entities from the provided text."""

            # Use LLM to extract entities
            formatted_prompt = prompt.format(text=text[:2000])  # Limit text length
            
            # Get response from LLM
            response = await self.llm.chat_sync(
                formatted_prompt,
                thread_id="entity_extraction",  # Use a dedicated thread
                digital_human_config={
                    'temperature': 0.3,  # Lower temperature for more consistent extraction
                    'max_tokens': 500
                }
            )
            
            # Parse the JSON response
            entities = self._parse_entity_response(response)
            
            logger.info(f"Extracted {len(entities)} entities from text")
            return entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities: {str(e)}")
            return []
    
    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract entities"""
        try:
            # Try to find JSON array in the response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                entities = json.loads(json_str)
                
                # Validate and clean entities
                valid_entities = []
                for entity in entities:
                    if isinstance(entity, dict) and 'name' in entity and 'type' in entity:
                        valid_entities.append({
                            'name': str(entity['name'])[:100],  # Limit name length
                            'type': str(entity.get('type', 'other')).lower(),
                            'context': str(entity.get('context', ''))[:200]  # Limit context length
                        })
                
                return valid_entities
            else:
                logger.warning("No JSON array found in LLM response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entity JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing entities: {str(e)}")
            return []
    
    async def store_entities(
        self,
        entities: List[Dict[str, Any]],
        memory_id: str,
        digital_human_id: str
    ) -> List[Dict[str, Any]]:
        """
        Store entities in Neo4j and create relationships with memory
        
        Args:
            entities: List of entity dictionaries
            memory_id: The memory node ID to link entities to
            digital_human_id: The digital human these entities belong to
        
        Returns:
            List of created entity nodes
        """
        try:
            created_entities = []
            
            # Find the memory node
            memory_node = self.graph.nodes.find_by_property('Memory', 'memory_id', memory_id)
            if not memory_node:
                logger.warning(f"Memory node {memory_id} not found")
                return []
            
            for entity in entities:
                # Find or create entity node
                entity_node = await self._find_or_create_entity(
                    name=entity['name'],
                    entity_type=entity['type'],
                    context=entity.get('context', ''),
                    digital_human_id=digital_human_id
                )
                
                if entity_node:
                    # Create MENTIONS relationship between memory and entity
                    self.graph.relationships.create(
                        from_id=memory_node['id'],
                        to_id=entity_node['id'],
                        type='MENTIONS',
                        properties={
                            'context': entity.get('context', ''),
                            'created_at': datetime.now().isoformat()
                        }
                    )
                    
                    created_entities.append(entity_node)
            
            # Update co-occurrence relationships between entities
            if len(entities) > 1:
                await self.update_entity_relationships(entities, digital_human_id)
            
            logger.info(f"Stored {len(created_entities)} entities for memory {memory_id}")
            return created_entities
            
        except Exception as e:
            logger.error(f"Failed to store entities: {str(e)}")
            return []
    
    async def _find_or_create_entity(
        self,
        name: str,
        entity_type: str,
        context: str,
        digital_human_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find existing entity or create new one"""
        try:
            # Check if entity already exists for this digital human
            existing = self.graph.nodes.find_by_property('Entity', 'name', name)
            
            # Filter for this digital human
            for node in [existing] if existing and not isinstance(existing, list) else (existing or []):
                if node.get('properties', {}).get('digital_human_id') == digital_human_id:
                    # Entity exists, update frequency
                    current_frequency = node['properties'].get('frequency', 0)
                    self.graph.nodes.update(node['id'], {
                        'frequency': current_frequency + 1,
                        'last_mentioned': datetime.now().isoformat()
                    })
                    return node
            
            # Create new entity
            entity_node = self.graph.nodes.create(
                label='Entity',
                properties={
                    'name': name,
                    'type': entity_type,
                    'context': context,
                    'digital_human_id': digital_human_id,
                    'frequency': 1,
                    'first_mentioned': datetime.now().isoformat(),
                    'last_mentioned': datetime.now().isoformat()
                }
            )
            
            return entity_node
                
        except Exception as e:
            logger.error(f"Failed to find or create entity: {str(e)}")
            return None
    
    async def find_entity_relationships(
        self,
        entity_name: str,
        digital_human_id: str,
        relationship_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Find relationships between entities
        
        Args:
            entity_name: Name of the entity to find relationships for
            digital_human_id: The digital human context
            relationship_depth: How many hops to traverse
        
        Returns:
            Dictionary with entity and its relationships
        """
        try:
            query = """
            MATCH (e:Entity {name: $name, digital_human_id: $dh_id})
            OPTIONAL MATCH path = (e)-[*1..%d]-(related:Entity)
            WHERE related.digital_human_id = $dh_id
            RETURN e, collect(DISTINCT {
                entity: related.name,
                type: related.type,
                relationship: [r in relationships(path) | type(r)][0]
            }) as relationships
            """ % relationship_depth
            
            results = self.graph.execute_cypher(query, {
                'name': entity_name,
                'dh_id': digital_human_id
            })
            
            if results:
                return {
                    'entity': entity_name,
                    'relationships': results[0]['relationships']
                }
            
            return {'entity': entity_name, 'relationships': []}
            
        except Exception as e:
            logger.error(f"Failed to find entity relationships: {str(e)}")
            return {'entity': entity_name, 'relationships': []}
    
    async def update_entity_relationships(
        self,
        entities: List[Dict[str, Any]],
        digital_human_id: str
    ):
        """
        Update relationships between entities that appear together
        
        Args:
            entities: List of entities that appeared together
            digital_human_id: The digital human context
        """
        try:
            # Create CO_OCCURS relationships between entities that appear together
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    # Find both entity nodes
                    node1 = self.graph.nodes.find_by_property('Entity', 'name', entity1['name'])
                    node2 = self.graph.nodes.find_by_property('Entity', 'name', entity2['name'])
                    
                    if node1 and node2:
                        # Check if both belong to the same digital human
                        if (node1.get('properties', {}).get('digital_human_id') == digital_human_id and
                            node2.get('properties', {}).get('digital_human_id') == digital_human_id):
                            
                            # Check if relationship already exists using Cypher
                            check_query = """
                            MATCH (n1)-[r:CO_OCCURS]-(n2)
                            WHERE id(n1) = $id1 AND id(n2) = $id2
                            RETURN r
                            """
                            existing_rels = self.graph.execute_cypher(check_query, {
                                'id1': node1['id'],
                                'id2': node2['id']
                            })
                            
                            if existing_rels:
                                # Update co-occurrence count
                                update_query = """
                                MATCH (n1)-[r:CO_OCCURS]-(n2)
                                WHERE id(n1) = $id1 AND id(n2) = $id2
                                SET r.count = r.count + 1,
                                    r.last_seen = $last_seen
                                """
                                self.graph.execute_cypher(update_query, {
                                    'id1': node1['id'],
                                    'id2': node2['id'],
                                    'last_seen': datetime.now().isoformat()
                                })
                            else:
                                # Create new co-occurrence relationship
                                self.graph.relationships.create(
                                    from_id=node1['id'],
                                    to_id=node2['id'],
                                    type='CO_OCCURS',
                                    properties={
                                        'count': 1,
                                        'first_seen': datetime.now().isoformat(),
                                        'last_seen': datetime.now().isoformat()
                                    }
                                )
            
            logger.debug(f"Updated relationships for {len(entities)} entities")
            
        except Exception as e:
            logger.error(f"Failed to update entity relationships: {str(e)}")
    
    async def get_entity_context(
        self,
        entity_name: str,
        digital_human_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get context for an entity including memories that mention it
        
        Args:
            entity_name: Name of the entity
            digital_human_id: The digital human context
            limit: Maximum number of memories to return
        
        Returns:
            Dictionary with entity information and related memories
        """
        try:
            query = """
            MATCH (e:Entity {name: $name, digital_human_id: $dh_id})
            OPTIONAL MATCH (m:Memory)-[:MENTIONS]->(e)
            RETURN e as entity,
                   collect(DISTINCT {
                       memory_id: m.memory_id,
                       summary: m.summary,
                       importance: m.importance
                   })[..%d] as memories
            """ % limit
            
            results = self.graph.execute_cypher(query, {
                'name': entity_name,
                'dh_id': digital_human_id
            })
            
            if results:
                entity_data = results[0]['entity']
                memories = results[0]['memories']
                
                return {
                    'entity': {
                        'name': entity_data.get('name'),
                        'type': entity_data.get('type'),
                        'context': entity_data.get('context'),
                        'frequency': entity_data.get('frequency', 0),
                        'first_mentioned': entity_data.get('first_mentioned'),
                        'last_mentioned': entity_data.get('last_mentioned')
                    },
                    'memories': [m for m in memories if m.get('memory_id')]  # Filter out null memories
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get entity context: {str(e)}")
            return None