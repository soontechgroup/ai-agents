import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.digital_human_training_service import DigitalHumanTrainingService
from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.graph_service import GraphService
from app.services.hybrid_search_service import HybridSearchService
from app.services.embedding_service import EmbeddingService


class TestEmbeddingGraphIntegration:
    """测试向量数据库和图数据库的集成"""

    @pytest.mark.asyncio
    async def test_end_to_end_embedding_and_search(self):
        """端到端测试：提取知识 -> 生成嵌入 -> 存储 -> 搜索"""

        # 1. 准备 mock 服务
        mock_training_message_repo = Mock()
        mock_training_message_repo.create_training_message = Mock(return_value=Mock(id=1))

        # Mock 知识提取器
        mock_knowledge_extractor = AsyncMock()
        mock_knowledge_extractor.extract_with_embeddings = AsyncMock(return_value={
            "entities": [
                {
                    "name": "Python",
                    "type": "skill",
                    "types": ["skill", "technology"],
                    "description": "编程语言",
                    "confidence": 0.9,
                    "embedding_id": "embed-python-123",
                    "properties": {}
                },
                {
                    "name": "机器学习",
                    "type": "skill",
                    "types": ["skill", "ai"],
                    "description": "AI技术",
                    "confidence": 0.85,
                    "embedding_id": "embed-ml-456",
                    "properties": {}
                }
            ],
            "relationships": [
                {
                    "source": "Python",
                    "target": "机器学习",
                    "relation_type": "用于",
                    "types": ["USED_FOR"],
                    "description": "Python用于机器学习",
                    "confidence": 0.8,
                    "embedding_id": "embed-rel-789",
                    "properties": {}
                }
            ]
        })

        # Mock 图服务
        mock_graph_service = Mock()
        stored_entities = []
        stored_relationships = []

        async def store_entity(dh_id, entity):
            stored_entities.append(entity)
            return True

        async def store_relationship(dh_id, rel):
            stored_relationships.append(rel)
            return True

        mock_graph_service.store_digital_human_entity = AsyncMock(side_effect=store_entity)
        mock_graph_service.store_digital_human_relationship = AsyncMock(side_effect=store_relationship)
        mock_graph_service.get_digital_human_knowledge_context = Mock(return_value={
            "total_knowledge_points": 2,
            "categories": {}
        })

        # Mock 混合搜索服务
        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search = AsyncMock(return_value={
            "entities": [
                {
                    "name": "Python",
                    "types": ["skill"],
                    "description": "编程语言",
                    "confidence": 0.9,
                    "distance": 0.1,
                    "embedding_id": "embed-python-123"
                }
            ],
            "relationships": [],
            "statistics": {
                "total_entities": 1,
                "total_relationships": 0
            }
        })

        # 2. 创建训练服务
        training_service = DigitalHumanTrainingService(
            training_message_repo=mock_training_message_repo,
            knowledge_extractor=mock_knowledge_extractor,
            graph_service=mock_graph_service,
            hybrid_search_service=mock_hybrid_search,
            db_session_factory=Mock()
        )

        # 3. 执行知识提取（应该生成嵌入）
        state = {
            "digital_human_id": 123,
            "user_id": 1,
            "current_message": "我擅长Python和机器学习",
            "should_extract": True,
            "step_results": {}
        }

        result = await training_service._extract_knowledge(state)

        # 4. 验证提取结果包含embedding_id
        assert "extracted_knowledge" in result
        entities = result["extracted_knowledge"]["entities"]
        assert len(entities) == 2
        assert all("embedding_id" in e for e in entities)

        # 5. 验证实体被存储时包含embedding_id
        assert len(stored_entities) == 2
        assert stored_entities[0]["embedding_id"] == "embed-python-123"
        assert stored_entities[1]["embedding_id"] == "embed-ml-456"

        # 6. 验证关系被存储时包含embedding_id
        assert len(stored_relationships) == 1
        assert stored_relationships[0]["embedding_id"] == "embed-rel-789"

        # 7. 执行搜索测试
        search_state = {
            "digital_human_id": 123,
            "user_id": 1,
            "current_message": "Python相关的技能",
            "messages": []
        }

        search_result = await training_service._search_memory(search_state)

        # 8. 验证搜索结果
        assert "memory_search_results" in search_result
        assert search_result["memory_search_results"]["statistics"]["total_entities"] == 1

        # 9. 验证搜索调用包含正确的digital_human_id
        mock_hybrid_search.search.assert_called_with(
            query="Python相关的技能",
            digital_human_id=123,
            mode="hybrid",
            entity_limit=5,
            relationship_limit=3,
            expand_graph=True
        )

    @pytest.mark.asyncio
    async def test_embedding_id_consistency(self):
        """测试embedding_id在不同组件间的一致性"""

        # Mock embedding服务
        mock_embedding_service = AsyncMock()
        generated_embed_id = "consistent-embed-123"
        mock_embedding_service.embed_entity = AsyncMock(return_value={
            "embedding_id": generated_embed_id,
            "vector": [0.1, 0.2, 0.3],
            "text": "Entity: Test"
        })

        # Mock 知识提取器使用真实的embedding服务
        knowledge_extractor = KnowledgeExtractor()
        knowledge_extractor.embedding_service = mock_embedding_service

        # 执行提取
        with patch.object(knowledge_extractor, 'extract') as mock_extract:
            mock_extract.return_value = {
                "entities": [{"name": "Test", "type": "test", "properties": {}}],
                "relationships": []
            }

            result = await knowledge_extractor.extract_with_embeddings("test text", 456)

        # 验证embedding_id一致性
        assert result["entities"][0]["embedding_id"] == generated_embed_id

        # 验证embedding服务被正确调用
        mock_embedding_service.embed_entity.assert_called_once()
        call_args = mock_embedding_service.embed_entity.call_args
        assert call_args[0][1] == 456  # digital_human_id

    @pytest.mark.asyncio
    async def test_search_with_embedding_enrichment(self):
        """测试搜索结果能通过embedding_id关联到图数据"""

        # Mock 图仓库能通过embedding_id查询
        mock_graph_repo = Mock()
        mock_graph_repo.execute_cypher = Mock(return_value=(
            [["Python", "skill", "embed-python-123", {"extra": "data"}]],
            None
        ))

        # Mock embedding服务返回搜索结果
        mock_embedding_service = AsyncMock()
        mock_embedding_service.semantic_search = AsyncMock(return_value=[
            {
                "document": "Entity: Python",
                "metadata": {
                    "entity_name": "Python",
                    "embedding_id": "embed-python-123"  # 关键：通过这个ID关联
                },
                "distance": 0.1
            }
        ])

        # 创建混合搜索服务
        hybrid_search = HybridSearchService()
        hybrid_search.embedding_service = mock_embedding_service
        hybrid_search.extracted_knowledge_repo = mock_graph_repo

        # 执行搜索
        result = await hybrid_search.search(
            query="Python",
            digital_human_id=789,
            mode="semantic"
        )

        # 验证搜索结果
        assert len(result["entities"]) > 0

        # 未来可以通过embedding_id从图数据库获取更多信息
        # 例如：根据embed-python-123查询Neo4j获取关联的其他实体