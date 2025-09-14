import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.embedding_service import EmbeddingService
import json


class TestEmbeddingService:
    """EmbeddingService 单元测试"""

    @pytest.fixture
    def mock_chroma_repo(self):
        """Mock ChromaRepository"""
        mock = Mock()
        mock.add_documents = Mock(return_value=True)
        mock.query_with_embedding = Mock(return_value={
            "documents": [["test doc"]],
            "metadatas": [[{"entity_name": "test"}]],
            "distances": [[0.5]],
            "ids": [["test-id"]]
        })
        return mock

    @pytest.fixture
    def mock_embeddings(self):
        """Mock OpenAI Embeddings"""
        mock = Mock()
        mock.embed_documents = Mock(return_value=[[0.1, 0.2, 0.3]])
        mock.embed_query = Mock(return_value=[0.1, 0.2, 0.3])
        return mock

    @pytest.fixture
    def embedding_service(self, mock_chroma_repo, mock_embeddings):
        """创建 EmbeddingService 实例"""
        with patch('app.services.embedding_service.ChromaRepository', return_value=mock_chroma_repo):
            with patch('app.services.embedding_service.OpenAIEmbeddings', return_value=mock_embeddings):
                service = EmbeddingService()
                service.chroma_repo = mock_chroma_repo
                service.embeddings = mock_embeddings
                return service

    @pytest.mark.asyncio
    async def test_embed_entity_with_digital_human_id(self, embedding_service, mock_chroma_repo):
        """测试实体向量化（包含 digital_human_id）"""
        # 准备测试数据
        entity = {
            "name": "Test Entity",
            "types": ["Person"],
            "description": "A test entity",
            "confidence": 0.9
        }
        digital_human_id = 123

        # 执行测试
        result = await embedding_service.embed_entity(entity, digital_human_id)

        # 验证结果
        assert result is not None
        assert "embedding_id" in result
        assert "vector" in result
        assert "text" in result

        # 验证 ChromaDB 调用
        mock_chroma_repo.add_documents.assert_called_once()
        call_args = mock_chroma_repo.add_documents.call_args

        # 验证 metadata 包含 digital_human_id
        metadata = call_args.kwargs["metadatas"][0]
        assert metadata["digital_human_id"] == str(digital_human_id)
        assert metadata["entity_name"] == "Test Entity"

    @pytest.mark.asyncio
    async def test_embed_relationship_with_digital_human_id(self, embedding_service, mock_chroma_repo):
        """测试关系向量化（包含 digital_human_id）"""
        # 准备测试数据
        relationship = {
            "source": "Entity A",
            "target": "Entity B",
            "types": ["KNOWS"],
            "description": "A knows B",
            "confidence": 0.8,
            "strength": 0.7
        }
        digital_human_id = 456

        # 执行测试
        result = await embedding_service.embed_relationship(relationship, digital_human_id)

        # 验证结果
        assert result is not None
        assert "embedding_id" in result

        # 验证 metadata 包含 digital_human_id
        call_args = mock_chroma_repo.add_documents.call_args
        metadata = call_args.kwargs["metadatas"][0]
        assert metadata["digital_human_id"] == str(digital_human_id)
        assert metadata["source"] == "Entity A"
        assert metadata["target"] == "Entity B"

    @pytest.mark.asyncio
    async def test_semantic_search_with_digital_human_filter(self, embedding_service, mock_chroma_repo):
        """测试语义搜索（数字人过滤）"""
        # 准备测试数据
        query = "test query"
        digital_human_id = 789

        # 执行搜索
        results = await embedding_service.semantic_search(
            query=query,
            collection="entity_embeddings",
            digital_human_id=digital_human_id,
            k=5
        )

        # 验证结果
        assert isinstance(results, list)
        assert len(results) == 1

        # 验证查询时包含了 digital_human_id 过滤
        call_args = mock_chroma_repo.query_with_embedding.call_args
        where_clause = call_args.kwargs["where"]
        assert where_clause["digital_human_id"] == str(digital_human_id)

    @pytest.mark.asyncio
    async def test_batch_embed_entities_with_cache(self, embedding_service, mock_chroma_repo):
        """测试批量实体向量化（带缓存）"""
        # 准备测试数据
        entities = [
            {"name": "Entity1", "types": ["Type1"], "description": "Desc1"},
            {"name": "Entity2", "types": ["Type2"], "description": "Desc2"}
        ]
        digital_human_id = 111

        # 第一次调用
        results1 = await embedding_service.batch_embed_entities(entities, digital_human_id)
        assert len(results1) == 2

        # 第二次调用（应该使用缓存）
        results2 = await embedding_service.batch_embed_entities(entities, digital_human_id)
        assert len(results2) == 2

        # 验证 ChromaDB 只调用了一次（第二次使用缓存）
        assert mock_chroma_repo.add_documents.call_count == 1

    @pytest.mark.asyncio
    async def test_embed_text_chunk_with_metadata(self, embedding_service, mock_chroma_repo):
        """测试文本块向量化（带元数据）"""
        # 准备测试数据
        text_chunk = "This is a test text chunk for embedding"
        digital_human_id = 222
        metadata = {"source": "test_source", "custom_field": "value"}

        # 执行测试
        result = await embedding_service.embed_text_chunk(
            chunk=text_chunk,
            digital_human_id=digital_human_id,
            metadata=metadata
        )

        # 验证结果
        assert result is not None
        assert "embedding_id" in result

        # 验证 metadata 合并正确
        call_args = mock_chroma_repo.add_documents.call_args
        stored_metadata = call_args.kwargs["metadatas"][0]
        assert stored_metadata["digital_human_id"] == str(digital_human_id)
        assert stored_metadata["source"] == "test_source"
        assert stored_metadata["custom_field"] == "value"
        assert "chunk_length" in stored_metadata

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, embedding_service, mock_chroma_repo):
        """测试多租户隔离性"""
        # 为不同数字人创建实体
        entity = {"name": "Shared Entity", "types": ["Type"], "description": "Desc"}

        # 数字人1的实体
        result1 = await embedding_service.embed_entity(entity, digital_human_id=1)

        # 数字人2的实体
        result2 = await embedding_service.embed_entity(entity, digital_human_id=2)

        # 验证两次调用都创建了新的 embedding（因为 digital_human_id 不同）
        assert mock_chroma_repo.add_documents.call_count == 2

        # 验证缓存键包含 digital_human_id
        # 使用正确的文本格式（与 _build_entity_text 方法一致）
        entity_text = "Entity: Shared Entity | Type: Type | Description: Desc"
        assert embedding_service.cache.get(embedding_service._get_cache_key(f"1:{entity_text}")) is not None
        assert embedding_service.cache.get(embedding_service._get_cache_key(f"2:{entity_text}")) is not None