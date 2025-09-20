import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from app.services.langgraph_service import LangGraphService
from app.services.conversation_service import ConversationService
from app.core.messages import UserMessage, AssistantMessage
from app.core.models import Conversation, Message, DigitalHuman
from app.schemas.conversation import ConversationCreate, MessageResponse
import json


class TestCheckpointerIntegration:

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = MagicMock()
        db.query = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        return db

    @pytest.fixture
    def mock_checkpointer(self):
        """模拟 checkpointer"""
        checkpointer = MagicMock()
        checkpointer.get = MagicMock(return_value={
            "channel_values": {
                "messages": []
            }
        })
        checkpointer.put = MagicMock()
        return checkpointer

    @pytest.fixture
    def langgraph_service(self, mock_checkpointer):
        """创建 LangGraphService 实例"""
        with patch('app.services.langgraph_service.MySQLCheckpointer', return_value=mock_checkpointer):
            with patch('app.services.langgraph_service.HybridSearchService'):
                with patch('app.services.langgraph_service.ChatOpenAI'):
                    service = LangGraphService()
                    service.checkpointer = mock_checkpointer
                    return service

    def test_chat_sync_uses_checkpointer(self, langgraph_service, mock_checkpointer):
        """测试同步聊天使用 checkpointer"""
        # 模拟 graph.invoke
        mock_result = MagicMock()
        mock_result.assistant_response = "Test response"
        langgraph_service.graph.invoke = MagicMock(return_value=mock_result)

        # 调用 chat_sync
        result = langgraph_service.chat_sync(
            message="Test message",
            thread_id="test-thread",
            digital_human_config={"id": 1, "name": "Test"}
        )

        # 验证 checkpointer.get 被调用
        mock_checkpointer.get.assert_called()

        # 验证 graph.invoke 被调用
        langgraph_service.graph.invoke.assert_called_once()

        # 验证返回正确的响应
        assert result == "Test response"

    def test_chat_stream_saves_intermediate_state(self, langgraph_service, mock_checkpointer):
        """测试流式聊天保存中间状态"""
        # 模拟记忆搜索返回结果
        with patch.object(langgraph_service, '_search_memory') as mock_search:
            mock_state = MagicMock()
            mock_state.messages = []
            mock_state.memory_context = "Test memory"
            mock_state.assistant_response = ""
            mock_search.return_value = mock_state

            with patch.object(langgraph_service, '_generate_ai_response_stream') as mock_generate:
                mock_generate.return_value = iter(["Test ", "response"])

                with patch.object(langgraph_service, '_process_user_input') as mock_process:
                    mock_process.return_value = mock_state

                    with patch.object(langgraph_service, '_finalize_response') as mock_finalize:
                        mock_finalize.return_value = mock_state

                        # 执行流式聊天
                        result = list(langgraph_service.chat_stream(
                            message="Test message",
                            thread_id="test-thread",
                            digital_human_config={"id": 1}
                        ))

                        # 验证 checkpointer.put 被调用两次（中间状态和最终状态）
                        assert mock_checkpointer.put.call_count == 2

                        # 检查第一次调用（中间状态）
                        first_call = mock_checkpointer.put.call_args_list[0]
                        assert first_call[0][1]["channel_values"]["memory_context"] == "Test memory"
                        assert first_call[0][2]["source"] == "stream_intermediate"

                        # 检查第二次调用（最终状态）
                        second_call = mock_checkpointer.put.call_args_list[1]
                        assert second_call[0][2]["source"] == "stream_final"

    def test_checkpointer_no_duplicate_messages(self, mock_db):
        """测试 checkpointer 不再重复保存消息"""
        from app.core.checkpointer import MySQLCheckpointer

        # 创建 checkpointer
        def mock_db_factory():
            yield mock_db

        checkpointer = MySQLCheckpointer(mock_db_factory)

        # 模拟查询对话
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = 1
        mock_conversation.last_message_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_conversation
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        # 调用 put 方法
        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {
            "v": 1,
            "ts": datetime.now().isoformat(),
            "channel_values": {
                "messages": [
                    {"role": "user", "content": "Test message"},
                    {"role": "assistant", "content": "Test response"}
                ]
            }
        }

        checkpointer.put(config, checkpoint, {}, {})

        # 验证没有创建 Message 对象
        message_calls = [call for call in mock_db.add.call_args_list if
                         hasattr(call[0][0], '__class__') and
                         call[0][0].__class__.__name__ == 'Message']
        assert len(message_calls) == 0

        # 验证更新了最后消息时间
        assert mock_conversation.last_message_at is not None

    def test_conversation_service_saves_messages_separately(self, mock_db):
        """测试 ConversationService 独立保存消息"""
        # 模拟仓储
        mock_conversation_repo = MagicMock()
        mock_message_repo = MagicMock()
        mock_langgraph_service = MagicMock()

        # 创建服务
        service = ConversationService(
            db=mock_db,
            langgraph_service=mock_langgraph_service
        )
        service.conversation_repo = mock_conversation_repo
        service.message_repo = mock_message_repo

        # 模拟对话
        mock_conversation = Mock(spec=Conversation)
        mock_conversation.id = 1
        mock_conversation.thread_id = "test-thread"
        mock_conversation.digital_human_id = 1

        mock_conversation_repo.get_conversation_by_id.return_value = mock_conversation

        # 模拟消息创建
        mock_user_msg = Mock(spec=Message)
        mock_user_msg.id = 1
        mock_user_msg.conversation_id = 1
        mock_user_msg.role = "user"
        mock_user_msg.content = "Test message"
        mock_user_msg.tokens_used = 10
        mock_user_msg.message_metadata = {}
        mock_user_msg.created_at = datetime.now()

        mock_ai_msg = Mock(spec=Message)
        mock_ai_msg.id = 2
        mock_ai_msg.conversation_id = 1
        mock_ai_msg.role = "assistant"
        mock_ai_msg.content = "Test response"
        mock_ai_msg.tokens_used = 20
        mock_ai_msg.message_metadata = {}
        mock_ai_msg.created_at = datetime.now()

        mock_message_repo.create_message.side_effect = [mock_user_msg, mock_ai_msg]
        mock_langgraph_service.chat_sync.return_value = "Test response"

        # 模拟数字人配置
        mock_digital_human = Mock(spec=DigitalHuman)
        mock_digital_human.id = 1
        mock_digital_human.name = "Test Digital Human"
        mock_digital_human.type = "专业助手"
        mock_digital_human.skills = []
        mock_digital_human.personality = {}
        mock_digital_human.conversation_style = "专业严谨"
        mock_digital_human.temperature = 0.7
        mock_digital_human.max_tokens = 2048
        mock_digital_human.system_prompt = "Test prompt"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_digital_human

        # 发送消息
        result = service.send_message(
            conversation_id=1,
            message_content="Test message",
            user_id=1
        )

        # 验证消息被保存两次（用户消息和AI响应）
        assert mock_message_repo.create_message.call_count == 2

        # 验证调用参数
        mock_message_repo.create_message.assert_any_call(1, "user", "Test message")
        mock_message_repo.create_message.assert_any_call(1, "assistant", "Test response")

    def test_checkpointer_version_management(self, mock_db):
        """测试 checkpointer 版本管理"""
        from app.core.checkpointer import MySQLCheckpointer
        from app.core.models import ConversationCheckpoint

        def mock_db_factory():
            yield mock_db

        checkpointer = MySQLCheckpointer(mock_db_factory)

        # 模拟已有版本
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (3,)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {"channel_values": {"messages": []}}

        checkpointer.put(config, checkpoint, {}, {})

        # 验证创建了新版本（版本4）
        add_calls = mock_db.add.call_args_list
        checkpoint_call = next((call for call in add_calls if
                                isinstance(call[0][0], ConversationCheckpoint)), None)

        assert checkpoint_call is not None
        assert checkpoint_call[0][0].version == 4
        assert checkpoint_call[0][0].parent_version == 3

    def test_stream_memory_notification(self, langgraph_service):
        """测试流式聊天返回记忆通知"""
        # 模拟有记忆上下文
        with patch.object(langgraph_service, '_search_memory') as mock_search:
            mock_state = MagicMock()
            mock_state.memory_context = "- Entity1\n- Entity2\n- Entity3"
            mock_state.messages = []
            mock_state.assistant_response = ""
            mock_search.return_value = mock_state

            with patch.object(langgraph_service, '_generate_ai_response_stream'):
                with patch.object(langgraph_service, '_process_user_input', return_value=mock_state):
                    with patch.object(langgraph_service, '_finalize_response', return_value=mock_state):
                        # 执行流式聊天
                        results = list(langgraph_service.chat_stream(
                            message="Test",
                            thread_id="test-thread",
                            digital_human_config={"id": 1}
                        ))

                        # 验证第一个结果是记忆通知
                        first_result = json.loads(results[0])
                        assert first_result["type"] == "memory"
                        assert "3 个相关记忆" in first_result["content"]
                        assert first_result["metadata"]["has_memory"] is True