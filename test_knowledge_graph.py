"""
Test script for Knowledge Graph storage implementation
"""

import asyncio
from datetime import datetime
from app.core.neomodel_config import init_neomodel
from app.repositories.neomodel.knowledge import KnowledgeRepository
from app.repositories.neomodel.entity import EntityRepository
from app.models.neomodel.knowledge import KnowledgeNode
from app.models.neomodel.entity import EntityNode
from app.core.logger import logger


async def test_knowledge_storage():
    """Test the knowledge graph storage functionality"""
    
    # Initialize Neomodel
    init_neomodel()
    logger.info("✅ Neomodel initialized")
    
    # Initialize repositories
    knowledge_repo = KnowledgeRepository()
    entity_repo = EntityRepository()
    
    # Test digital human ID
    digital_human_id = "test_dh_001"
    
    # 1. Create test entities
    logger.info("\n📌 Creating test entities...")
    
    python_entity = entity_repo.find_or_create(
        name="Python",
        entity_type="technology",
        digital_human_id=digital_human_id,
        description="A programming language"
    )
    logger.info(f"Created entity: {python_entity.name}")
    
    fastapi_entity = entity_repo.find_or_create(
        name="FastAPI",
        entity_type="technology",
        digital_human_id=digital_human_id,
        description="A modern web framework for Python"
    )
    logger.info(f"Created entity: {fastapi_entity.name}")
    
    # 2. Create test knowledge
    logger.info("\n📚 Creating test knowledge...")
    
    knowledge1 = KnowledgeNode(
        content="Python is a high-level programming language known for its simplicity and readability.",
        summary="Python programming language overview",
        category="fact",
        source="training",
        confidence=0.95,
        importance=0.8,
        digital_human_id=digital_human_id,
        keywords=["python", "programming", "language"]
    )
    knowledge1.save()
    logger.info(f"Created knowledge: {knowledge1.summary}")
    
    knowledge2 = KnowledgeNode(
        content="FastAPI is a modern, fast web framework for building APIs with Python based on standard Python type hints.",
        summary="FastAPI framework description",
        category="fact",
        source="training",
        confidence=0.9,
        importance=0.7,
        digital_human_id=digital_human_id,
        keywords=["fastapi", "api", "framework", "python"]
    )
    knowledge2.save()
    logger.info(f"Created knowledge: {knowledge2.summary}")
    
    # 3. Create relationships
    logger.info("\n🔗 Creating relationships...")
    
    # Knowledge mentions entities
    knowledge1.mentions_entities.connect(python_entity)
    logger.info(f"Connected: {knowledge1.summary} -> {python_entity.name}")
    
    knowledge2.mentions_entities.connect(fastapi_entity)
    knowledge2.mentions_entities.connect(python_entity)
    logger.info(f"Connected: {knowledge2.summary} -> {fastapi_entity.name}, {python_entity.name}")
    
    # Knowledge relates to knowledge
    # Note: Neomodel may not return relationship object directly
    knowledge2.related_to.connect(knowledge1)
    logger.info(f"Connected: {knowledge2.summary} RELATED_TO {knowledge1.summary}")
    
    # Entities co-occur
    python_entity.co_occurs_with.connect(fastapi_entity)
    logger.info(f"Connected: {python_entity.name} CO_OCCURS {fastapi_entity.name}")
    
    # 4. Test retrieval
    logger.info("\n🔍 Testing retrieval...")
    
    # Find knowledge by digital human
    dh_knowledge = knowledge_repo.find_by_digital_human(digital_human_id)
    logger.info(f"Found {len(dh_knowledge)} knowledge items for digital human")
    
    # Find knowledge by entities
    entity_knowledge = knowledge_repo.find_by_entities(
        ["Python", "FastAPI"],
        digital_human_id
    )
    logger.info(f"Found {len(entity_knowledge)} knowledge items mentioning entities")
    
    # Find related knowledge
    related = knowledge_repo.find_related_knowledge(knowledge1.uid)
    logger.info(f"Found {len(related)} related knowledge items")
    
    # Find co-occurring entities
    co_occurring = entity_repo.find_co_occurring(python_entity.uid)
    logger.info(f"Found {len(co_occurring)} co-occurring entities")
    
    # 5. Test search
    logger.info("\n🔎 Testing search...")
    
    search_results = knowledge_repo.search_by_content(
        "framework",
        digital_human_id
    )
    logger.info(f"Search found {len(search_results)} results for 'framework'")
    
    # 6. Test statistics
    logger.info("\n📊 Testing statistics...")
    
    stats = knowledge_repo.get_knowledge_graph_stats(digital_human_id)
    logger.info(f"Knowledge graph stats: {stats}")
    
    # 7. Test knowledge update
    logger.info("\n✏️ Testing knowledge updates...")
    
    knowledge1.validate(confidence=1.0)
    logger.info(f"Validated knowledge: {knowledge1.summary}")
    
    knowledge1.update_usage()
    logger.info(f"Updated usage for: {knowledge1.summary}")
    
    # 8. Test entity updates
    logger.info("\n✏️ Testing entity updates...")
    
    python_entity.update_mention()
    logger.info(f"Updated mention count for: {python_entity.name}")
    
    python_entity.add_alias("Python3")
    logger.info(f"Added alias 'Python3' to: {python_entity.name}")
    
    python_entity.set_attribute("version", "3.9+")
    logger.info(f"Set attribute 'version' for: {python_entity.name}")
    
    logger.info("\n✅ All tests completed successfully!")
    
    return {
        "knowledge_created": 2,
        "entities_created": 2,
        "relationships_created": 5,
        "tests_passed": True
    }


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_knowledge_storage())
    print(f"\nTest Results: {result}")