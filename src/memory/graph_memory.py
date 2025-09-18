"""
LangGraph-inspired memory system with conditional routing and tool integration
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time
import uuid

from .base import BaseMemorySystem, MemoryItem, RetrievalResult

class ProcessingStage(Enum):
    PARSE_INPUT = "parse_input"
    CLASSIFY_INTENT = "classify_intent"
    EXTRACT_FACTS = "extract_facts"
    EVALUATE_TOOLS = "evaluate_tools"
    EXECUTE_TOOLS = "execute_tools"
    STORE_MEMORY = "store_memory"
    RETRIEVE_CONTEXT = "retrieve_context"
    COMBINE_RESULTS = "combine_results"
    GENERATE_RESPONSE = "generate_response"

@dataclass
class ConversationState:
    """State object that flows through the processing graph"""
    user_message: str = ""
    assistant_response: str = ""
    query: str = ""
    
    # Intent and analysis
    intent: str = "conversational"
    intent_confidence: float = 0.0
    needs_web_search: bool = False
    
    # Extracted information
    facts: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    
    # Tool results
    web_search_results: List[Dict[str, Any]] = field(default_factory=list)
    tool_context: str = ""
    
    # Memory results
    retrieved_memories: List[str] = field(default_factory=list)
    memory_context: str = ""
    
    # Processing metadata
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    processing_stages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class GraphMemorySystem(BaseMemorySystem):
    """LangGraph-inspired memory system with conditional routing"""
    
    def __init__(self, name: str = "Graph Memory System"):
        super().__init__(name)
        self.processing_nodes = {
            ProcessingStage.PARSE_INPUT: self._parse_input_node,
            ProcessingStage.CLASSIFY_INTENT: self._classify_intent_node,
            ProcessingStage.EXTRACT_FACTS: self._extract_facts_node,
            ProcessingStage.EVALUATE_TOOLS: self._evaluate_tools_node,
            ProcessingStage.EXECUTE_TOOLS: self._execute_tools_node,
            ProcessingStage.STORE_MEMORY: self._store_memory_node,
            ProcessingStage.RETRIEVE_CONTEXT: self._retrieve_context_node,
            ProcessingStage.COMBINE_RESULTS: self._combine_results_node,
        }
        
    def store_conversation(self, user_message: str, assistant_response: str, context: Dict[str, Any] = None):
        """Store conversation using graph workflow"""
        
        # Create conversation state
        state = ConversationState(
            user_message=user_message,
            assistant_response=assistant_response
        )
        
        if context:
            state.conversation_id = context.get('conversation_id', state.conversation_id)
        
        # Execute storage workflow
        state = self._execute_storage_workflow(state)
        
        if not state.errors:
            self.conversation_count += 1
            print(f"[GRAPH] Stored conversation {self.conversation_count}")
        else:
            print(f"[ERROR] Storage failed: {state.errors}")
    
    def retrieve_context(self, query: str, max_results: int = 5) -> RetrievalResult:
        """Retrieve context using graph workflow"""
        
        # Create retrieval state
        state = ConversationState(query=query)
        
        # Execute retrieval workflow
        state = self._execute_retrieval_workflow(state)
        
        # Convert state to RetrievalResult
        return RetrievalResult(
            memories=state.retrieved_memories[:max_results],
            context=state.retrieved_memories[:3],  # Top 3 for context
            facts=state.facts,
            web_results=state.web_search_results,
            confidence=state.intent_confidence,
            sources=self._extract_sources(state),
            metadata={
                'intent': state.intent,
                'processing_stages': state.processing_stages,
                'used_web_search': state.needs_web_search,
                'conversation_id': state.conversation_id
            }
        )
    
    def _execute_storage_workflow(self, state: ConversationState) -> ConversationState:
        """Execute the storage workflow graph"""
        
        # Storage workflow: Parse → Extract Facts → Store
        workflow_stages = [
            ProcessingStage.PARSE_INPUT,
            ProcessingStage.EXTRACT_FACTS,
            ProcessingStage.STORE_MEMORY
        ]
        
        for stage in workflow_stages:
            state = self._execute_node(stage, state)
            if state.errors:
                break
        
        return state
    
    def _execute_retrieval_workflow(self, state: ConversationState) -> ConversationState:
        """Execute the retrieval workflow graph"""
        
        # Retrieval workflow: Parse → Classify Intent → Evaluate Tools → Execute Tools → Retrieve → Combine
        workflow_stages = [
            ProcessingStage.PARSE_INPUT,
            ProcessingStage.CLASSIFY_INTENT,
            ProcessingStage.EVALUATE_TOOLS
        ]
        
        # Execute initial stages
        for stage in workflow_stages:
            state = self._execute_node(stage, state)
            if state.errors:
                break
        
        # Conditional tool execution
        if state.needs_web_search:
            state = self._execute_node(ProcessingStage.EXECUTE_TOOLS, state)
        
        # Continue with memory retrieval and combination
        remaining_stages = [
            ProcessingStage.RETRIEVE_CONTEXT,
            ProcessingStage.COMBINE_RESULTS
        ]
        
        for stage in remaining_stages:
            state = self._execute_node(stage, state)
            if state.errors:
                break
        
        return state
    
    def _execute_node(self, stage: ProcessingStage, state: ConversationState) -> ConversationState:
        """Execute a single processing node"""
        try:
            state.processing_stages.append(stage.value)
            
            if stage in self.processing_nodes:
                state = self.processing_nodes[stage](state)
            else:
                state.errors.append(f"Unknown processing stage: {stage}")
            
            return state
            
        except Exception as e:
            state.errors.append(f"Node {stage.value} failed: {str(e)}")
            return state
    
    # Processing Node Implementations
    
    def _parse_input_node(self, state: ConversationState) -> ConversationState:
        """Parse input and extract basic structure"""
        
        text = state.user_message if state.user_message else state.query
        
        # Basic entity extraction (simple implementation)
        import re
        
        # Extract potential names (capitalized words)
        names = re.findall(r'\b[A-Z][a-z]+\b', text)
        state.entities.extend(names)
        
        # Remove duplicates
        state.entities = list(set(state.entities))
        
        return state
    
    def _classify_intent_node(self, state: ConversationState) -> ConversationState:
        """Classify the intent of the user query"""
        
        query = state.query.lower()
        
        # Simple intent classification
        if any(word in query for word in ['latest', 'recent', 'current', 'news', 'today', 'now']):
            state.intent = "current_information"
            state.intent_confidence = 0.8
        elif any(word in query for word in ['what is', 'who is', 'define', 'explain']):
            state.intent = "factual_question"
            state.intent_confidence = 0.7
        elif any(word in query for word in ['how to', 'help me', 'tutorial', 'guide']):
            state.intent = "instructional"
            state.intent_confidence = 0.7
        else:
            state.intent = "conversational"
            state.intent_confidence = 0.5
        
        return state
    
    def _extract_facts_node(self, state: ConversationState) -> ConversationState:
        """Extract structured facts from the conversation"""
        
        if state.user_message and state.assistant_response:
            facts = self.extract_facts(state.user_message, state.assistant_response)
            state.facts.update(facts)
        
        return state
    
    def _evaluate_tools_node(self, state: ConversationState) -> ConversationState:
        """Evaluate if web search tools are needed"""
        
        query = state.query.lower()
        
        # Determine if web search is needed
        web_search_indicators = [
            'latest', 'recent', 'current', 'news', 'today', 'now',
            'search for', 'find information about', 'what happened',
            'update on', 'status of'
        ]
        
        state.needs_web_search = any(indicator in query for indicator in web_search_indicators)
        
        # Also check intent
        if state.intent == "current_information":
            state.needs_web_search = True
        
        return state
    
    def _execute_tools_node(self, state: ConversationState) -> ConversationState:
        """Execute web search tools if needed"""
        
        if state.needs_web_search:
            # Import web search tool
            try:
                from ..tools.web_search import WebSearchTool
                
                search_tool = WebSearchTool()
                results = search_tool.search(state.query, max_results=5)
                
                state.web_search_results = results
                
                # Create tool context from search results
                if results:
                    context_parts = []
                    for result in results[:3]:  # Top 3 results
                        context_parts.append(f"• {result.get('title', '')}: {result.get('snippet', '')}")
                    
                    state.tool_context = "Recent information found:\n" + "\n".join(context_parts)
                
            except Exception as e:
                state.errors.append(f"Web search failed: {str(e)}")
        
        return state
    
    def _store_memory_node(self, state: ConversationState) -> ConversationState:
        """Store the conversation in memory"""
        
        if not self.collection:
            state.errors.append("No ChromaDB collection available")
            return state
        
        try:
            # Create memory document
            memory_content = f"User: {state.user_message}\nAssistant: {state.assistant_response}"
            
            # Get embedding
            embedding = self.get_embedding(memory_content)
            
            # Prepare metadata
            metadata = {
                'user_message': state.user_message,
                'assistant_response': state.assistant_response,
                'timestamp': str(state.timestamp),
                'conversation_id': state.conversation_id,
                'intent': state.intent,
                'entities': ','.join(state.entities),
                'facts_count': str(len(state.facts))
            }
            
            # Add facts to metadata (convert to strings)
            for key, value in state.facts.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[f'fact_{key}'] = str(value)
            
            # Store in ChromaDB
            doc_id = f"conv_{state.conversation_id}_{int(state.timestamp)}"
            
            self.collection.add(
                documents=[memory_content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            print(f"[GRAPH] Stored memory: {doc_id}")
            
        except Exception as e:
            state.errors.append(f"Memory storage failed: {str(e)}")
        
        return state
    
    def _retrieve_context_node(self, state: ConversationState) -> ConversationState:
        """Retrieve relevant memories from storage"""
        
        if not self.collection:
            state.errors.append("No ChromaDB collection available")
            return state
        
        try:
            # Get query embedding
            query_embedding = self.get_embedding(state.query)
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=5
            )
            
            if results['documents'] and results['documents'][0]:
                state.retrieved_memories = results['documents'][0]
                
                # Extract facts from metadata
                if results['metadatas'] and results['metadatas'][0]:
                    for metadata in results['metadatas'][0]:
                        for key, value in metadata.items():
                            if key.startswith('fact_'):
                                fact_key = key[5:]  # Remove 'fact_' prefix
                                state.facts[fact_key] = value
            
        except Exception as e:
            state.errors.append(f"Memory retrieval failed: {str(e)}")
        
        return state
    
    def _combine_results_node(self, state: ConversationState) -> ConversationState:
        """Combine memory and tool results"""
        
        # Combine memory context
        if state.retrieved_memories:
            state.memory_context = "Previous conversations:\n" + "\n".join([
                f"• {memory[:100]}..." for memory in state.retrieved_memories[:3]
            ])
        
        return state
    
    def _extract_sources(self, state: ConversationState) -> List[str]:
        """Extract sources from the processing state"""
        sources = []
        
        if state.retrieved_memories:
            sources.append("Memory")
        
        if state.web_search_results:
            sources.append("Web Search")
            # Add specific URLs if available
            for result in state.web_search_results:
                if 'url' in result:
                    sources.append(result['url'])
        
        return sources
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        
        doc_count = 0
        if self.collection:
            try:
                doc_count = self.collection.count()
            except:
                doc_count = 0
        
        return {
            "system_name": self.name,
            "conversation_count": self.conversation_count,
            "stored_documents": doc_count,
            "features": [
                "LangGraph-inspired workflows",
                "Conditional tool routing",
                "Web search integration",
                "Fact extraction",
                "ChromaDB persistent storage",
                "OpenAI embeddings"
            ],
            "processing_stages": [stage.value for stage in ProcessingStage]
        }