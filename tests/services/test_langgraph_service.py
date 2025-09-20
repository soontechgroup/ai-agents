import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.services.langgraph_service import LangGraphService, ConversationState
from app.core.messages import UserMessage, AssistantMessage, SystemMessage
import os


class TestLangGraphService:
    """LangGraphService 测试类"""

    @pytest.fixture
    def mock_hybrid_search_service(self):
        """模拟 HybridSearchService"""
        mock_service = Mock()
        mock_service.search = AsyncMock(return_value={
            "entities": [
                {"name": "Python", "description": "一种高级编程语言"},
                {"name": "Django", "description": "Python Web框架"},
                {"name": "Flask", "description": "轻量级Python Web框架"}
            ],
            "relationships": [
                {"source": "Python", "target": "Django", "description": "Django基于Python开发"},
                {"source": "Python", "target": "Flask", "description": "Flask是Python框架"}
            ],
            "statistics": {
                "total_entities": 3,
                "total_relationships": 2
            }
        })
        return mock_service

    @pytest.fixture
    def mock_checkpointer(self):
        """模拟 MySQLCheckpointer"""
        mock = Mock()
        mock.get = Mock(return_value={
            "channel_values": {
                "messages": []
            }
        })
        mock.put = Mock()
        return mock

    @pytest.fixture
    def langgraph_service(self, mock_hybrid_search_service, mock_checkpointer):
        """创建带有模拟依赖的 LangGraphService 实例"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('app.services.langgraph_service.ChatOpenAI'):
                with patch('app.services.langgraph_service.HybridSearchService', return_value=mock_hybrid_search_service):
                    with patch('app.services.langgraph_service.MySQLCheckpointer', return_value=mock_checkpointer):
                        service = LangGraphService()
                        service.hybrid_search_service = mock_hybrid_search_service
                        service.checkpointer = mock_checkpointer
                        return service

    def test_format_memory_context_with_entities_and_relationships(self, langgraph_service):
        """测试格式化包含实体和关系的记忆上下文"""
        search_results = {
            "entities": [
                {"name": "Python", "description": "一种高级编程语言"},
                {"name": "Django", "description": "Python Web框架"},
                {"name": "Flask", "description": "轻量级Python Web框架"},
                {"name": "FastAPI", "description": "现代Web API框架"},
                {"name": "SQLAlchemy", "description": "Python ORM库"},
                {"name": "Pytest", "description": "Python测试框架"}
            ],
            "relationships": [
                {"source": "Python", "target": "Django", "description": "Django基于Python开发"},
                {"source": "Python", "target": "Flask", "description": "Flask是Python框架"},
                {"source": "Python", "target": "FastAPI", "types": "使用"},
                {"source": "Django", "target": "SQLAlchemy"}
            ]
        }

        result = langgraph_service._format_memory_context(search_results)

        # 验证格式化结果
        assert "相关记忆：" in result
        assert "Python: 一种高级编程语言" in result
        assert "Django: Python Web框架" in result

        # 验证只取前5个实体
        assert "Pytest" not in result  # 第6个实体不应该出现

        # 验证关系格式化
        assert "相关关系：" in result
        assert "Python → Django: Django基于Python开发" in result

        # 验证只取前3个关系
        assert "Django → SQLAlchemy" not in result  # 第4个关系不应该出现

    def test_format_memory_context_empty_results(self, langgraph_service):
        """测试格式化空的搜索结果"""
        search_results = {
            "entities": [],
            "relationships": []
        }

        result = langgraph_service._format_memory_context(search_results)

        assert result == ""

    def test_format_memory_context_only_entities(self, langgraph_service):
        """测试只有实体没有关系的情况"""
        search_results = {
            "entities": [
                {"name": "Python", "description": "编程语言"},
                {"name": "Java"}  # 没有描述
            ],
            "relationships": []
        }

        result = langgraph_service._format_memory_context(search_results)

        assert "相关记忆：" in result
        assert "Python: 编程语言" in result
        assert "- Java" in result  # 没有描述的实体
        assert "相关关系：" not in result  # 没有关系部分

    def test_search_memory_with_digital_human_id(self, langgraph_service):
        """测试带数字人ID的记忆搜索"""
        state = ConversationState(
            user_message="介绍一下Python",
            digital_human_config={"id": 1, "name": "测试助手"},
            messages=[]
        )

        result_state = langgraph_service._search_memory(state)

        # 验证调用了搜索服务
        langgraph_service.hybrid_search_service.search.assert_called_once()
        call_args = langgraph_service.hybrid_search_service.search.call_args[1]
        assert call_args["query"] == "介绍一下Python"
        assert call_args["digital_human_id"] == 1

        # 验证记忆上下文被设置
        assert result_state.memory_context != ""
        assert "相关记忆：" in result_state.memory_context

    def test_search_memory_without_digital_human_id(self, langgraph_service):
        """测试没有数字人ID的情况"""
        state = ConversationState(
            user_message="你好",
            digital_human_config={"name": "测试助手"},  # 没有id
            messages=[]
        )

        result_state = langgraph_service._search_memory(state)

        # 验证没有调用搜索服务
        langgraph_service.hybrid_search_service.search.assert_not_called()

        # 验证记忆上下文为空
        assert result_state.memory_context == ""

    def test_search_memory_with_exception(self, langgraph_service):
        """测试记忆搜索失败的情况"""
        # 模拟搜索失败
        langgraph_service.hybrid_search_service.search = AsyncMock(
            side_effect=Exception("搜索服务错误")
        )

        state = ConversationState(
            user_message="测试消息",
            digital_human_config={"id": 1},
            messages=[]
        )

        # 搜索失败不应该抛出异常
        result_state = langgraph_service._search_memory(state)

        # 验证记忆上下文为空，但流程继续
        assert result_state.memory_context == ""

    def test_generate_ai_response_with_memory_context(self, langgraph_service):
        """测试带记忆上下文的AI响应生成"""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "基于您提到的Python，这是一种广泛使用的编程语言。"
        mock_llm.invoke = Mock(return_value=mock_response)
        langgraph_service.llm = mock_llm

        state = ConversationState(
            user_message="介绍Python",
            digital_human_config={
                "temperature": 0.5,
                "max_tokens": 150,
                "system_prompt": "你是编程专家"
            },
            memory_context="相关记忆：\n- Python: 一种高级编程语言",
            messages=[]
        )

        result_state = langgraph_service._generate_ai_response(state)

        # 验证LLM被调用
        mock_llm.invoke.assert_called_once()

        # 验证系统提示包含记忆上下文
        messages = mock_llm.invoke.call_args[0][0]
        system_message = messages[0]
        assert isinstance(system_message, SystemMessage)
        assert "基于以下相关记忆回答用户" in system_message.content
        assert "Python: 一种高级编程语言" in system_message.content

        # 验证响应被设置
        assert result_state.assistant_response == "基于您提到的Python，这是一种广泛使用的编程语言。"

    def test_process_user_input(self, langgraph_service):
        """测试处理用户输入"""
        state = ConversationState(
            user_message="测试消息",
            messages=[]
        )

        result_state = langgraph_service._process_user_input(state)

        # 验证消息被添加到历史
        assert len(result_state.messages) == 1
        assert isinstance(result_state.messages[0], UserMessage)
        assert result_state.messages[0].content == "测试消息"

    def test_finalize_response(self, langgraph_service):
        """测试完成响应处理"""
        state = ConversationState(
            assistant_response="AI的回复",
            messages=[]
        )

        result_state = langgraph_service._finalize_response(state)

        # 验证助手消息被添加到历史
        assert len(result_state.messages) == 1
        assert isinstance(result_state.messages[0], AssistantMessage)
        assert result_state.messages[0].content == "AI的回复"

    @pytest.mark.asyncio
    async def test_chat_stream_with_memory(self, langgraph_service):
        """测试流式聊天的记忆集成"""
        # 模拟 _generate_ai_response_stream
        def mock_stream_generator(state):
            yield "这是"
            yield "流式"
            yield "响应"
            state.assistant_response = "这是流式响应"

        langgraph_service._generate_ai_response_stream = mock_stream_generator

        # 收集所有流式输出
        outputs = []
        for chunk in langgraph_service.chat_stream(
            message="测试消息",
            thread_id="test-thread",
            digital_human_config={"id": 1, "name": "测试助手"}
        ):
            outputs.append(chunk)

        # 验证输出
        assert len(outputs) > 0

        # 第一个输出应该是记忆信息（JSON格式）
        import json
        if outputs[0].startswith("{"):
            memory_info = json.loads(outputs[0])
            assert memory_info["type"] == "memory"
            assert "找到" in memory_info["content"]
            assert "相关记忆" in memory_info["content"]

    def test_build_system_prompt_with_personality(self, langgraph_service):
        """测试构建包含个性的系统提示"""
        config = {
            "system_prompt": "基础提示",
            "personality": {
                "professionalism": 90,
                "friendliness": 85,
                "humor": 60
            },
            "skills": ["Python", "JavaScript"],
            "conversation_style": "专业友好"
        }

        prompt = langgraph_service._build_system_prompt(config)

        assert "基础提示" in prompt
        assert "专业性: 90/100" in prompt
        assert "友善度: 85/100" in prompt
        assert "幽默感: 60/100" in prompt
        assert "专业技能: Python, JavaScript" in prompt
        assert "对话风格: 专业友好" in prompt