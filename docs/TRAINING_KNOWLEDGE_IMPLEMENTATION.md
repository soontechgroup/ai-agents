# Training & Knowledge System Implementation Plan

## 📋 Overview

This document outlines the complete implementation plan for adding a training mode and knowledge storage system to the AI Agents project. The system enables digital humans to learn from training sessions, store knowledge in Neo4j, and use that knowledge to provide intelligent responses.

## 🎯 Project Goals

1. **Training Mode**: Allow users to teach digital humans through structured training sessions
2. **Knowledge Extraction**: Extract and structure knowledge from training conversations
3. **Knowledge Storage**: Store knowledge in Neo4j graph database with relationships
4. **Intelligent Retrieval**: Use vector search + graph expansion for context-aware responses
5. **Knowledge Management**: Support validation, updates, and contradiction detection

## 🏗️ Architecture

### System Flow
```
Training Mode:
[User Input] → [Training API] → [Knowledge Extraction] → [Neo4j Storage]
                                           ↓
                                    [Entity Extraction]
                                           ↓
                                    [Relationship Creation]

Chat Mode:
[User Query] → [Vector Search (Chroma)] → [Entity Matching] → [Graph Expansion (Neo4j)]
                                                                        ↓
                                                              [Context Building]
                                                                        ↓
                                                              [Response Generation]
```

### Technology Stack
- **Backend**: FastAPI (Python)
- **Vector Database**: ChromaDB (similarity search)
- **Graph Database**: Neo4j with Neomodel ORM (knowledge relationships)
- **LLM**: LangChain/LangGraph for extraction and generation
- **Embedding**: OpenAI/Local embeddings for vector search

## 📦 Current Implementation Status

### ✅ Completed Components

#### 1. Neo4j Knowledge Models (`app/models/neomodel/`)
- **KnowledgeNode** (`knowledge.py`)
  - Stores extracted knowledge with categories (fact, experience, preference, skill, rule, concept)
  - Tracks confidence, validation status, importance, usage
  - Supports relationships to other knowledge, entities, memories
  
- **EntityNode** (`entity.py`)
  - Represents people, places, concepts mentioned in knowledge
  - Tracks co-occurrence with other entities
  - Supports hierarchical relationships

#### 2. Repository Layer (`app/repositories/neomodel/`)
- **KnowledgeRepository** (`knowledge.py`)
  - CRUD operations for knowledge
  - Search by content, entities, digital human
  - Find contradictions and related knowledge
  - Knowledge graph statistics
  
- **EntityRepository** (`entity.py`)
  - Entity management (find, create, merge)
  - Co-occurrence tracking
  - Entity network analysis

#### 3. Test Implementation (`test_knowledge_graph.py`)
- Validates Neo4j connection
- Tests node creation and relationships
- Demonstrates basic knowledge graph operations

### 🚧 Pending Implementation

#### 1. Knowledge Service (`app/services/knowledge_service.py`)
```python
class KnowledgeService:
    """
    Main service for knowledge management
    - Extract knowledge from text
    - Store with proper categorization
    - Handle contradictions
    - Manage knowledge lifecycle
    """
    
    async def extract_knowledge_from_training(
        self, 
        text: str, 
        digital_human_id: str,
        context: Dict
    ) -> List[KnowledgeNode]
    
    async def validate_knowledge(
        self,
        knowledge_id: str,
        user_feedback: str
    ) -> bool
    
    async def retrieve_relevant_knowledge(
        self,
        query: str,
        digital_human_id: str,
        limit: int = 10
    ) -> List[Dict]
```

#### 2. Training Mode API (`app/api/v1/endpoints/training.py`)
```python
@router.post("/training/start")
async def start_training_session(
    digital_human_id: str,
    user_id: str
) -> TrainingSession

@router.post("/training/teach")
async def teach_knowledge(
    session_id: str,
    content: str,
    category: str
) -> KnowledgeResponse

@router.post("/training/validate")
async def validate_extracted_knowledge(
    knowledge_id: str,
    is_correct: bool,
    correction: Optional[str]
) -> ValidationResponse

@router.post("/training/end")
async def end_training_session(
    session_id: str
) -> SessionSummary
```

#### 3. Enhanced Conversation Service
- Modify `app/services/conversation_service.py` to:
  - Query knowledge graph during conversations
  - Use retrieved knowledge in responses
  - Track knowledge usage for importance scoring

#### 4. Knowledge Retrieval Pipeline
```python
class KnowledgeRetriever:
    """
    Hybrid retrieval combining vector and graph search
    """
    
    async def retrieve(self, query: str, digital_human_id: str):
        # 1. Vector similarity search in Chroma
        similar_memories = await self.chroma.search(query)
        
        # 2. Extract entities from query and memories
        entities = await self.entity_extractor.extract(query)
        
        # 3. Find knowledge mentioning these entities
        entity_knowledge = await self.knowledge_repo.find_by_entities(entities)
        
        # 4. Graph expansion - find related knowledge
        expanded = await self.expand_knowledge_graph(entity_knowledge)
        
        # 5. Rank and return combined results
        return self.rank_knowledge(similar_memories + entity_knowledge + expanded)
```

#### 5. Graph Expansion Algorithm
```python
async def expand_knowledge_graph(
    self,
    initial_knowledge: List[KnowledgeNode],
    max_depth: int = 2
) -> List[KnowledgeNode]:
    """
    Expand from initial knowledge nodes through relationships
    - Follow RELATED_TO relationships
    - Include knowledge with same entities
    - Consider contradiction relationships
    """
```

## 🗄️ Database Schema

### Neo4j Nodes

#### KnowledgeNode
```cypher
(k:KnowledgeNode {
    uid: "unique_id",
    content: "Full knowledge text",
    summary: "Brief summary",
    category: "fact|experience|preference|skill|rule|concept",
    source: "training|conversation|document|inference",
    confidence: 0.95,
    validation_status: "unvalidated|validated|disputed|deprecated",
    importance: 0.8,
    digital_human_id: "dh_001",
    learned_at: datetime,
    keywords: ["python", "programming"],
    context: {additional_metadata}
})
```

#### EntityNode
```cypher
(e:EntityNode {
    uid: "unique_id",
    name: "Python",
    entity_type: "technology",
    description: "Programming language",
    digital_human_id: "dh_001",
    mention_count: 15,
    importance_score: 0.9,
    aliases: ["Python3", "CPython"]
})
```

### Relationships
```cypher
// Knowledge relationships
(k1:KnowledgeNode)-[:RELATED_TO {strength: 0.8}]->(k2:KnowledgeNode)
(k1:KnowledgeNode)-[:CONTRADICTS {reason: "..."}]->(k2:KnowledgeNode)
(k1:KnowledgeNode)-[:SUPPORTS]->(k2:KnowledgeNode)

// Entity relationships
(k:KnowledgeNode)-[:MENTIONS]->(e:EntityNode)
(e1:EntityNode)-[:CO_OCCURS {count: 5}]->(e2:EntityNode)
(e1:EntityNode)-[:PARENT_OF]->(e2:EntityNode)

// Memory integration (future)
(k:KnowledgeNode)-[:DERIVED_FROM]->(m:MemoryNode)
```

## 📝 Implementation Steps

### Phase 1: Core Knowledge Service (Priority: High)
1. Create `app/services/knowledge_service.py`
   - Knowledge extraction logic using LLM
   - Categorization and confidence scoring
   - Entity extraction integration
   - Contradiction detection

2. Integrate with existing `EntityExtractor`
   - Enhance entity extraction for knowledge context
   - Build entity co-occurrence tracking
   - Create entity hierarchy management

### Phase 2: Training API (Priority: High)
1. Create `app/api/v1/endpoints/training.py`
   - Session management endpoints
   - Real-time knowledge extraction via SSE
   - Validation and feedback loops
   - Training progress tracking

2. Create schemas in `app/schemas/training.py`
   ```python
   class TrainingSessionCreate(BaseModel)
   class KnowledgeTeachRequest(BaseModel)
   class KnowledgeValidationRequest(BaseModel)
   class TrainingSessionResponse(BaseModel)
   ```

### Phase 3: Retrieval Enhancement (Priority: High)
1. Create `app/services/knowledge_retriever.py`
   - Hybrid search implementation
   - Graph expansion algorithm
   - Result ranking and scoring
   - Context building for responses

2. Modify `app/services/conversation_service.py`
   - Add knowledge retrieval step
   - Integrate knowledge into prompts
   - Track knowledge usage

### Phase 4: Frontend Integration (Priority: Medium)
1. Create training mode UI in `ai-agents-frontend/`
   - Training session interface
   - Knowledge validation UI
   - Real-time extraction feedback
   - Progress indicators

2. Add knowledge visualization
   - Graph view of knowledge relationships
   - Entity network visualization
   - Knowledge search interface

### Phase 5: Advanced Features (Priority: Low)
1. Knowledge lifecycle management
   - Automatic decay for unused knowledge
   - Knowledge consolidation
   - Version control for updates

2. Import/Export functionality
   - Knowledge graph export to JSON/CSV
   - Bulk import from documents
   - Knowledge sharing between digital humans

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_knowledge_service.py
- Test knowledge extraction accuracy
- Test entity extraction
- Test contradiction detection
- Test confidence scoring

# tests/test_knowledge_repository.py  
- Test CRUD operations
- Test search functionality
- Test relationship management
```

### Integration Tests
```python
# tests/test_training_flow.py
- Test complete training session flow
- Test knowledge persistence
- Test retrieval in conversations
```

### Performance Tests
- Graph query performance with large datasets
- Vector search latency
- Concurrent training sessions

## 🚀 Quick Start Commands

### Start Services
```bash
# Start all databases
docker-compose up -d

# Run application
python run.py --env dev --reload
```

### Test Knowledge Graph
```bash
# Run test script
python test_knowledge_graph.py

# Access Neo4j Browser
open http://localhost:7474
# Username: neo4j, Password: password123
```

### Useful Cypher Queries
```cypher
// View all knowledge for a digital human
MATCH (k:KnowledgeNode {digital_human_id: "dh_001"})
RETURN k.summary, k.category, k.confidence
ORDER BY k.importance DESC

// Find knowledge network
MATCH path = (k1:KnowledgeNode)-[*1..2]-(k2:KnowledgeNode)
WHERE k1.uid = "knowledge_id"
RETURN path

// Find entities and their knowledge
MATCH (e:EntityNode)<-[:MENTIONS]-(k:KnowledgeNode)
RETURN e.name, collect(k.summary) as knowledge
```

## 📚 API Examples

### Training Mode
```python
# Start training session
POST /api/v1/training/start
{
    "digital_human_id": "dh_001",
    "user_id": "user_123"
}

# Teach knowledge
POST /api/v1/training/teach
{
    "session_id": "session_456",
    "content": "Python is a high-level programming language",
    "category": "fact"
}

# Response includes extracted knowledge
{
    "knowledge_id": "k_789",
    "summary": "Python programming language characteristics",
    "entities": ["Python"],
    "confidence": 0.95,
    "requires_validation": false
}
```

### Knowledge Retrieval
```python
# In conversation
POST /api/v1/conversations/chat
{
    "digital_human_id": "dh_001",
    "message": "What do you know about Python?"
}

# System internally:
# 1. Searches for "Python" in vectors
# 2. Finds Python entity in graph
# 3. Retrieves related knowledge
# 4. Expands through relationships
# 5. Generates response with context
```

## 🔧 Configuration

### Environment Variables (.env.dev)
```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=neo4j

# Knowledge Extraction
KNOWLEDGE_EXTRACTION_MODEL=gpt-3.5-turbo
KNOWLEDGE_CONFIDENCE_THRESHOLD=0.7
KNOWLEDGE_MAX_EXTRACTION_PER_SESSION=100
```

### Knowledge Categories Configuration
```python
# app/core/knowledge_config.py
KNOWLEDGE_CATEGORIES = {
    "fact": {"min_confidence": 0.8, "requires_validation": False},
    "experience": {"min_confidence": 0.7, "requires_validation": True},
    "preference": {"min_confidence": 0.6, "requires_validation": True},
    "skill": {"min_confidence": 0.8, "requires_validation": False},
    "rule": {"min_confidence": 0.9, "requires_validation": True},
    "concept": {"min_confidence": 0.7, "requires_validation": False}
}
```

## 📊 Monitoring & Analytics

### Key Metrics
- Knowledge extraction rate (knowledge/session)
- Validation accuracy (validated/total)
- Knowledge usage frequency
- Contradiction detection rate
- Retrieval relevance scores

### Dashboard Queries
```cypher
// Knowledge statistics
MATCH (k:KnowledgeNode)
RETURN 
  k.category as category,
  count(k) as count,
  avg(k.confidence) as avg_confidence,
  avg(k.importance) as avg_importance

// Most mentioned entities
MATCH (e:EntityNode)<-[:MENTIONS]-(k:KnowledgeNode)
RETURN e.name, count(k) as mentions
ORDER BY mentions DESC
LIMIT 10
```

## 🤝 Team Collaboration

### Code Style
- Follow existing project patterns
- Use type hints for all functions
- Document complex algorithms
- Write tests for new features

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/training-mode

# Regular commits
git add .
git commit -m "feat: implement knowledge extraction service"

# Push to remote
git push origin feature/training-mode
```

### Review Checklist
- [ ] Code follows project style
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Logging added for debugging

## 📞 Support & Resources

### Internal Documentation
- `CLAUDE.md` - Project AI assistant guidelines
- `docs/architecture-zh.md` - System architecture
- `README.md` - Project setup

### External Resources
- [Neomodel Documentation](https://neomodel.readthedocs.io/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [LangChain Documentation](https://docs.langchain.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🎯 Next Session Quick Start

To continue implementation in a new session:

1. **Review this document** for context
2. **Check completed items** in the status section
3. **Start with the next pending component**
4. **Run tests** to ensure everything still works
5. **Follow the implementation steps** sequentially

### Immediate Next Steps
1. Implement `KnowledgeService` class
2. Create training API endpoints
3. Test knowledge extraction flow
4. Integrate with conversation service

---

*Last Updated: 2025-08-27*
*Branch: dev/neo4j (to be moved to feature/training)*