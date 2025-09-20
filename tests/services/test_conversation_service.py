import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from app.services.conversation_service import ConversationService
from app.services.langgraph_service import LangGraphService
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationPageRequest
from app.core.models import DigitalHuman, Conversation, Message
import json


class TestConversationService:
    """ConversationService 测试类"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = Mock(spec=Session)
        return db

    @pytest.fixture
    def mock_langgraph_service(self):
        """模拟 LangGraphService"""
        service = Mock(spec=LangGraphService)
        service.create_thread_id = Mock(return_value="test-thread-123")
        service.chat_sync = Mock(return_value="这是AI的回复")
        service.chat_stream = Mock(return_value=iter(["这是", "流式", "回复"]))
        service.clear_conversation = Mock(return_value=True)
        return service

    @pytest.fixture
    def mock_conversation_repo(self):
        """模拟对话仓库"""
        from datetime import datetime
        repo = Mock()
        repo.create_conversation = Mock(return_value=Mock(
            id=1,
            title="测试对话",
            digital_human_id=1,
            thread_id="test-thread-123",
            user_id=1,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_message_at=datetime.now()
        ))
        repo.get_conversation_by_id = Mock(return_value=Mock(
            id=1,
            title="测试对话",
            digital_human_id=1,
            thread_id="test-thread-123",
            user_id=1,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_message_at=datetime.now()
        ))
        repo.get_conversations_paginated = Mock(return_value=([], 0))
        repo.update_conversation = Mock(return_value=Mock(
            id=1,
            title="更新后的对话",
            digital_human_id=1,
            thread_id="test-thread-123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_message_at=datetime.now()
        ))
        repo.delete_conversation = Mock(return_value=True)
        return repo

    @pytest.fixture
    def mock_message_repo(self):
        """模拟消息仓库"""
        from datetime import datetime
        repo = Mock()
        repo.create_message = Mock(return_value=Mock(
            id=1,
            conversation_id=1,
            role="user",
            content="测试消息",
            tokens_used=10,
            message_metadata={},
            created_at=datetime.now()
        ))
        repo.get_conversation_messages = Mock(return_value=[])
        repo.delete_conversation_messages = Mock(return_value=True)
        return repo

    @pytest.fixture
    def conversation_service(self, mock_db, mock_langgraph_service, mock_conversation_repo, mock_message_repo):
        """创建带有模拟依赖的 ConversationService 实例"""
        service = ConversationService(mock_db, mock_langgraph_service)
        service.conversation_repo = mock_conversation_repo
        service.message_repo = mock_message_repo
        return service

    @pytest.fixture
    def mock_digital_human(self):
        """模拟数字人对象"""
        digital_human = Mock(spec=DigitalHuman)
        digital_human.id = 1
        digital_human.name = "Python专家"
        digital_human.type = "assistant"
        digital_human.skills = ["Python", "编程教学"]
        digital_human.personality = {"professionalism": 90, "friendliness": 85}
        digital_human.conversation_style = "专业友好"
        digital_human.temperature = 0.7
        digital_human.max_tokens = 2048
        digital_human.system_prompt = "你是一个Python编程专家"
        return digital_human

    def test_get_digital_human_config_with_id(self, conversation_service, mock_db, mock_digital_human):
        """测试获取数字人配置（包含ID）"""
        # 模拟数据库查询
        mock_db.query.return_value.filter.return_value.first.return_value = mock_digital_human

        config = conversation_service._get_digital_human_config(1)

        # 验证配置包含ID
        assert config["id"] == 1
        assert config["name"] == "Python专家"
        assert config["type"] == "assistant"
        assert config["skills"] == ["Python", "编程教学"]
        assert config["temperature"] == 0.7
        assert config["max_tokens"] == 2048
        assert config["system_prompt"] == "你是一个Python编程专家"

    def test_get_digital_human_config_not_found(self, conversation_service, mock_db):
        """测试数字人不存在的情况"""
        # 模拟数据库查询返回空
        mock_db.query.return_value.filter.return_value.first.return_value = None

        config = conversation_service._get_digital_human_config(999)

        # 验证返回空配置
        assert config == {}

    def test_create_conversation(self, conversation_service):
        """测试创建对话"""
        conversation_data = ConversationCreate(
            digital_human_id=1,
            title="测试对话"
        )

        result = conversation_service.create_conversation(conversation_data, user_id=1)

        # 验证调用了正确的方法
        conversation_service.langgraph_service.create_thread_id.assert_called_once()
        conversation_service.conversation_repo.create_conversation.assert_called_once_with(
            conversation_data, 1, "test-thread-123"
        )

        # 验证返回结果
        assert result.id == 1
        assert result.title == "测试对话"

    def test_send_message_with_memory(self, conversation_service, mock_db, mock_digital_human):
        """测试发送消息（包含记忆搜索）"""
        # 模拟数据库查询数字人
        mock_db.query.return_value.filter.return_value.first.return_value = mock_digital_human

        # 模拟对话存在
        mock_conversation = Mock(digital_human_id=1, thread_id="test-thread-123")
        conversation_service.conversation_repo.get_conversation_by_id.return_value = mock_conversation

        # 发送消息
        result = conversation_service.send_message(
            conversation_id=1,
            message_content="介绍一下Python",
            user_id=1
        )

        # 验证调用了LangGraph服务
        conversation_service.langgraph_service.chat_sync.assert_called_once()

        # 验证传递了包含ID的配置
        call_args = conversation_service.langgraph_service.chat_sync.call_args
        # chat_sync 的参数是 (message, thread_id, digital_human_config)
        digital_human_config = call_args[0][2]  # 第三个位置参数
        assert digital_human_config["id"] == 1  # 确保ID被传递

        # 验证创建了消息
        assert conversation_service.message_repo.create_message.call_count == 2  # 用户消息和AI消息

    def test_send_message_stream_with_memory(self, conversation_service, mock_db, mock_digital_human):
        """测试流式发送消息（包含记忆搜索）"""
        # 模拟数据库查询数字人
        mock_db.query.return_value.filter.return_value.first.return_value = mock_digital_human

        # 模拟对话存在
        mock_conversation = Mock(digital_human_id=1, thread_id="test-thread-123")
        conversation_service.conversation_repo.get_conversation_by_id.return_value = mock_conversation

        # 收集流式输出
        outputs = list(conversation_service.send_message_stream(
            conversation_id=1,
            message_content="Python有哪些Web框架？",
            user_id=1
        ))

        # 验证输出不为空
        assert len(outputs) > 0

        # 验证第一个输出是用户消息确认
        first_output = json.loads(outputs[0])
        assert first_output["type"] == "message"

        # 验证调用了LangGraph的流式方法
        conversation_service.langgraph_service.chat_stream.assert_called_once()

        # 验证传递了包含ID的配置
        call_args = conversation_service.langgraph_service.chat_stream.call_args
        # chat_stream 的参数是 (message, thread_id, digital_human_config)
        digital_human_config = call_args[0][2]  # 第三个位置参数
        assert digital_human_config["id"] == 1

    def test_get_conversation_with_messages(self, conversation_service):
        """测试获取包含消息的对话"""
        from datetime import datetime
        # 模拟消息
        mock_messages = [
            Mock(id=1, conversation_id=1, role="user", content="你好", tokens_used=5, message_metadata={}, created_at=datetime.now()),
            Mock(id=2, conversation_id=1, role="assistant", content="你好！有什么可以帮助你的吗？", tokens_used=10, message_metadata={}, created_at=datetime.now())
        ]
        conversation_service.message_repo.get_conversation_messages.return_value = mock_messages

        result = conversation_service.get_conversation_with_messages(
            conversation_id=1,
            user_id=1,
            message_limit=10
        )

        # 验证结果
        assert result is not None
        assert result.id == 1
        assert len(result.messages) == 2
        assert result.messages[0].content == "你好"
        assert result.messages[1].content == "你好！有什么可以帮助你的吗？"

    def test_clear_conversation_history(self, conversation_service):
        """测试清除对话历史"""
        result = conversation_service.clear_conversation_history(
            conversation_id=1,
            user_id=1
        )

        # 验证调用了正确的方法
        conversation_service.message_repo.delete_conversation_messages.assert_called_once_with(1)
        conversation_service.langgraph_service.clear_conversation.assert_called_once()

        assert result is True

    def test_send_message_conversation_not_found(self, conversation_service):
        """测试对话不存在时发送消息"""
        # 模拟对话不存在
        conversation_service.conversation_repo.get_conversation_by_id.return_value = None

        result = conversation_service.send_message(
            conversation_id=999,
            message_content="测试",
            user_id=1
        )

        # 验证返回None
        assert result is None

        # 验证没有调用LangGraph服务
        conversation_service.langgraph_service.chat_sync.assert_not_called()

    def test_send_message_stream_error_handling(self, conversation_service, mock_db, mock_digital_human):
        """测试流式发送消息的错误处理"""
        # 模拟数据库查询数字人
        mock_db.query.return_value.filter.return_value.first.return_value = mock_digital_human

        # 模拟对话存在
        mock_conversation = Mock(digital_human_id=1, thread_id="test-thread-123")
        conversation_service.conversation_repo.get_conversation_by_id.return_value = mock_conversation

        # 模拟LangGraph抛出异常
        conversation_service.langgraph_service.chat_stream.side_effect = ValueError("API错误")

        # 收集流式输出
        outputs = list(conversation_service.send_message_stream(
            conversation_id=1,
            message_content="测试",
            user_id=1
        ))

        # 验证有错误输出
        assert len(outputs) > 0

        # 找到错误消息
        error_found = False
        for output in outputs:
            data = json.loads(output)
            if data.get("type") == "error":
                error_found = True
                # 验证错误消息包含 "API错误" 或 "AI响应生成失败"
                assert "API错误" in data["content"] or "AI响应生成失败" in data["content"]
                break

        assert error_found, "应该包含错误消息"