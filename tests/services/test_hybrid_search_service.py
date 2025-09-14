import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.hybrid_search_service import HybridSearchService


class TestHybridSearchService:
    """HybridSearchService 单元测试"""

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock EmbeddingService"""
        mock = Mock()
        mock.semantic_search = AsyncMock(return_value=[
            {
                "document": "test doc",
                "metadata": {
                    "entity_name": "Test Entity",
                    "entity_types": '["Person"]',
                    "description": "A test entity",
                    "confidence": "0.9"
                },
                "distance": 0.3,
                "id": "entity-1"
            }
        ])
        return mock

    @pytest.fixture
    def mock_graph_repo(self):
        """Mock Graph Repository"""
        mock = Mock()
        return mock

    @pytest.fixture
    def hybrid_search_service(self, mock_embedding_service, mock_graph_repo):
        """创建 HybridSearchService 实例"""
        with patch('app.services.hybrid_search_service.EmbeddingService', return_value=mock_embedding_service):
            with patch('app.services.hybrid_search_service.ExtractedKnowledgeRepository', return_value=mock_graph_repo):
                service = HybridSearchService()
                service.embedding_service = mock_embedding_service
                service.extracted_knowledge_repo = mock_graph_repo
                return service

    @pytest.mark.asyncio
    async def test_search_semantic_mode(self, hybrid_search_service, mock_embedding_service):
        """测试纯语义搜索模式"""
        # 执行语义搜索
        result = await hybrid_search_service.search(
            query="test query",
            digital_human_id=123,
            mode="semantic",
            entity_limit=10,
            relationship_limit=5
        )

        # 验证结果结构
        assert "entities" in result
        assert "relationships" in result
        assert "statistics" in result
        assert result["mode"] == "semantic"

        # 验证调用了 embedding_service
        assert mock_embedding_service.semantic_search.call_count == 2  # entities + relationships

        # 验证 digital_human_id 被传递
        calls = mock_embedding_service.semantic_search.call_args_list
        for call in calls:
            assert call.kwargs["digital_human_id"] == 123

    @pytest.mark.asyncio
    async def test_search_graph_mode(self, hybrid_search_service):
        """测试纯图搜索模式"""
        # Mock _get_graph_neighbors
        hybrid_search_service._get_graph_neighbors = AsyncMock(return_value={
            "entities": [
                {"name": "Graph Entity", "types": ["Type"], "description": "From graph", "confidence": 0.7}
            ],
            "relationships": []
        })

        # 先添加一些实体用于图扩展
        result = await hybrid_search_service.search(
            query="test query",
            digital_human_id=456,
            mode="semantic",  # 先用语义搜索获取初始实体
            entity_limit=5
        )

        # 执行图搜索
        result = await hybrid_search_service.search(
            query="test query",
            digital_human_id=456,
            mode="graph",
            expand_graph=True
        )

        # 验证图扩展被调用
        if result["entities"]:
            hybrid_search_service._get_graph_neighbors.assert_called()

    @pytest.mark.asyncio
    async def test_search_hybrid_mode(self, hybrid_search_service, mock_embedding_service):
        """测试混合搜索模式"""
        # Mock graph neighbors
        hybrid_search_service._get_graph_neighbors = AsyncMock(return_value={
            "entities": [
                {"name": "Graph Entity", "types": ["Type"], "description": "From graph", "confidence": 0.7}
            ],
            "relationships": [
                {
                    "source": "Test Entity",
                    "target": "Graph Entity",
                    "types": ["RELATES_TO"],
                    "description": "Relation",
                    "confidence": 0.6,
                    "strength": 0.5
                }
            ]
        })

        # 执行混合搜索
        result = await hybrid_search_service.search(
            query="test query",
            digital_human_id=789,
            mode="hybrid",
            entity_limit=10,
            relationship_limit=5,
            expand_graph=True
        )

        # 验证结果包含语义和图搜索结果
        assert len(result["entities"]) > 0
        assert result["statistics"]["total_entities"] > 0

        # 验证 digital_human_id 传递给所有方法
        calls = mock_embedding_service.semantic_search.call_args_list
        for call in calls:
            assert call.kwargs["digital_human_id"] == 789

    @pytest.mark.asyncio
    async def test_search_entities_only(self, hybrid_search_service, mock_embedding_service):
        """测试仅搜索实体"""
        # 执行实体搜索
        results = await hybrid_search_service.search_entities(
            query="entity query",
            digital_human_id=111,
            k=5
        )

        # 验证调用了 semantic_search
        mock_embedding_service.semantic_search.assert_called_with(
            query="entity query",
            collection="entity_embeddings",
            digital_human_id=111,
            k=5
        )

        # 验证返回结果
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_relationships_only(self, hybrid_search_service, mock_embedding_service):
        """测试仅搜索关系"""
        # 执行关系搜索
        results = await hybrid_search_service.search_relationships(
            query="relationship query",
            digital_human_id=222,
            k=3
        )

        # 验证调用了 semantic_search
        mock_embedding_service.semantic_search.assert_called_with(
            query="relationship query",
            collection="relationship_embeddings",
            digital_human_id=222,
            k=3
        )

    @pytest.mark.asyncio
    async def test_search_text_chunks(self, hybrid_search_service, mock_embedding_service):
        """测试文本块搜索"""
        # 执行文本块搜索
        results = await hybrid_search_service.search_text_chunks(
            query="text query",
            digital_human_id=333,
            k=7
        )

        # 验证调用了 semantic_search
        mock_embedding_service.semantic_search.assert_called_with(
            query="text query",
            collection="text_chunk_embeddings",
            digital_human_id=333,
            k=7
        )

    @pytest.mark.asyncio
    async def test_deduplicate_and_rank(self, hybrid_search_service):
        """测试去重和排序功能"""
        # 准备带重复的结果
        results = {
            "entities": [
                {"name": "Entity1", "confidence": 0.9, "source": "semantic_search", "distance": 0.1},
                {"name": "Entity1", "confidence": 0.7, "source": "graph_expansion", "distance": 0.3},
                {"name": "Entity2", "confidence": 0.8, "source": "semantic_search", "distance": 0.2}
            ],
            "relationships": [
                {"source": "A", "target": "B", "confidence": 0.9, "source_type": "semantic_search"},
                {"source": "A", "target": "B", "confidence": 0.6, "source_type": "graph_expansion"}
            ]
        }

        # 执行去重和排序
        deduped = hybrid_search_service._deduplicate_and_rank(results)

        # 验证实体去重（应该只保留置信度高的）
        entity_names = [e["name"] for e in deduped["entities"]]
        assert entity_names.count("Entity1") == 1

        # 验证关系去重
        assert len(deduped["relationships"]) == 1

        # 验证排序（语义搜索结果优先）
        assert deduped["entities"][0]["source"] == "semantic_search"

    @pytest.mark.asyncio
    async def test_graph_neighbors_with_digital_human_filter(self, hybrid_search_service):
        """测试图邻居查询包含数字人过滤"""
        # Mock db.cypher_query
        with patch('app.services.hybrid_search_service.db') as mock_db:
            mock_db.cypher_query = Mock(return_value=(
                [
                    [
                        {"name": "Entity1", "type": "Person", "description": "Test"},
                        {"description": "knows"},
                        {"name": "Entity2", "type": "Person", "description": "Test2"}
                    ]
                ],
                None
            ))

            # 执行图邻居查询
            result = await hybrid_search_service._get_graph_neighbors(
                entity_name="Test Entity",
                digital_human_id=999
            )

            # 验证查询包含 digital_human_id
            call_args = mock_db.cypher_query.call_args
            query = call_args[0][0]
            params = call_args[0][1]

            assert "digital_human_id" in query.lower() or "dh" in query.lower()
            assert params["digital_human_id"] == 999

    @pytest.mark.asyncio
    async def test_multi_tenant_search_isolation(self, hybrid_search_service, mock_embedding_service):
        """测试多租户搜索隔离"""
        # 为数字人1搜索
        result1 = await hybrid_search_service.search(
            query="common query",
            digital_human_id=1,
            mode="semantic"
        )

        # 为数字人2搜索
        result2 = await hybrid_search_service.search(
            query="common query",
            digital_human_id=2,
            mode="semantic"
        )

        # 验证两次搜索都调用了 embedding_service，但带不同的 digital_human_id
        calls = mock_embedding_service.semantic_search.call_args_list
        dh_ids = [call.kwargs["digital_human_id"] for call in calls]

        assert 1 in dh_ids
        assert 2 in dh_ids