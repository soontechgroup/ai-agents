import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, Dict, Any
from datetime import datetime

from app.services.digital_human_training_service import (
    DigitalHumanTrainingService,
    TrainingState
)
from app.core.models import DigitalHumanTrainingMessage
from langchain.schema import HumanMessage, SystemMessage


class TestDigitalHumanTrainingService:
    
    @pytest.fixture
    def mock_training_message_repo(self):
        repo = Mock()
        message_counter = [0]
        
        def create_training_message_side_effect(**kwargs):
            message_counter[0] += 1
            msg = DigitalHumanTrainingMessage(
                id=message_counter[0],
                digital_human_id=kwargs.get('digital_human_id'),
                user_id=kwargs.get('user_id'),
                role=kwargs.get('role'),
                content=kwargs.get('content'),
                extracted_knowledge=kwargs.get('extracted_knowledge'),
                extraction_metadata=kwargs.get('extraction_metadata')
            )
            return msg
        
        repo.create_training_message = Mock(side_effect=create_training_message_side_effect)
        repo.commit = Mock()
        repo.rollback = Mock()
        return repo
    
    @pytest.fixture
    def mock_knowledge_extractor(self):
        extractor = AsyncMock()
        extractor.extract = AsyncMock(return_value={
            "entities": [
                {"name": "测试实体", "type": "person", "confidence": 0.9},
                {"name": "测试公司", "type": "organization", "confidence": 0.85}
            ],
            "relationships": [
                {
                    "source": "测试实体",
                    "target": "测试公司",
                    "relation_type": "工作于",
                    "confidence": 0.8
                }
            ]
        })
        return extractor
    
    @pytest.fixture
    def mock_graph_service(self):
        service = Mock()
        service.store_digital_human_entity = AsyncMock(return_value=True)
        service.store_digital_human_relationship = AsyncMock(return_value=True)
        service.get_digital_human_knowledge_context = Mock(return_value={
            "total_knowledge_points": 5,
            "categories": {
                "profession": {"count": 2, "examples": ["工程师", "开发者"]},
                "skill": {"count": 2, "examples": ["Python", "JavaScript"]},
                "project": {"count": 1, "examples": ["项目A"]}
            },
            "recent_entities": []
        })
        return service
    
    @pytest.fixture
    def mock_graph_repo(self):
        repo = Mock()
        repo.execute_query = Mock(return_value=[
            ("profession", ["工程师", "开发者"], 2),
            ("skill", ["Python", "JavaScript"], 2),
            ("project", ["项目A"], 1)
        ])
        return repo
    
    @pytest.fixture
    def mock_training_session_repo(self):
        repo = Mock()
        session = Mock()
        session.id = 1
        session.thread_id = "test-thread-123"
        session.digital_human_id = 1
        session.user_id = 1
        repo.get_or_create_session = Mock(return_value=session)
        repo.update_session = Mock()
        repo.commit = Mock()
        
        # 配置 add_message_to_session 返回具有可序列化 id 的 Mock 对象
        def create_message(session_id, digital_human_id, user_id, role, content):
            message = Mock()
            message.id = 100  # 使用数字而不是 Mock
            message.session_id = session_id
            message.digital_human_id = digital_human_id
            message.user_id = user_id
            message.role = role
            message.content = content
            message.extracted_knowledge = {}
            message.extraction_metadata = {}
            return message
        
        repo.add_message_to_session = Mock(side_effect=create_message)
        return repo
    
    @pytest.fixture
    async def training_service(self, mock_training_message_repo, mock_training_session_repo, mock_knowledge_extractor, mock_graph_service):
        return DigitalHumanTrainingService(
            training_message_repo=mock_training_message_repo,
            training_session_repo=mock_training_session_repo,
            knowledge_extractor=mock_knowledge_extractor,
            graph_service=mock_graph_service
        )
    
    @pytest.mark.asyncio
    async def test_intent_recognition_node(self, training_service):
        print("\n========== 测试意图识别节点 ==========")
        state = {
            "digital_human_id": 1,
            "user_id": 1,
            "current_message": "我是一名软件工程师，在阿里巴巴工作了5年",
            "messages": [],
            "extracted_knowledge": {},
            "knowledge_context": {},
            "next_question": "",
            "should_extract": False,
            "should_explore_deeper": False,
            "conversation_stage": "initial",
            "total_knowledge_points": 0,
            "categories": {},
            "current_step": "",
            "completed_steps": [],
            "step_results": {},
            "thinking_process": [],
            "events": []
        }
        print(f"输入消息: {state['current_message']}")
        
        result_state = training_service._recognize_intent(state)
        
        print(f"当前步骤: {result_state.get('current_step')}")
        print(f"已完成步骤: {result_state.get('completed_steps')}")
        intent = result_state.get('step_results', {}).get('intent_recognition', {}).get('intent', '未知')
        print(f"识别到的意图: {intent}")
        print(f"是否需要抽取知识: {result_state.get('should_extract')}")
        print(f"对话阶段: {result_state.get('conversation_stage')}")
        print(f"思考过程: {result_state.get('thinking_process')}")
        print(f"步骤结果: {result_state.get('step_results')}")
        print(f"事件数量: {len(result_state.get('events', []))}")
        print("=====================================\n")
        
        assert result_state.get('current_step') == "recognizing_intent"
        assert "intent_recognition" in result_state.get('completed_steps', [])
        assert "intent_recognition" in result_state.get('step_results', {})
        assert "intent" in result_state.get('step_results', {}).get("intent_recognition", {})
        assert isinstance(result_state.get('should_extract'), bool)
        assert len(result_state.get('thinking_process', [])) >= 2
        print(f"✅ 真实 AI 判断: intent = {intent}, should_extract = {result_state.get('should_extract')}")
    
    @pytest.mark.asyncio
    async def test_intent_recognition_json_error(self, training_service):
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="测试消息"
        )
        
        bad_response = Mock()
        bad_response.content = "这不是一个有效的JSON"
        original_llm = training_service.llm
        training_service.llm = Mock()
        training_service.llm.invoke = Mock(return_value=bad_response)
        
        with pytest.raises(ValueError, match="意图识别响应格式错误"):
            training_service._recognize_intent(state)
        
        training_service.llm = original_llm
    
    @pytest.mark.asyncio
    async def test_knowledge_extraction_node(self, training_service):
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="我在阿里巴巴工作",
            should_extract=True
        )
        
        result_state = await training_service._extract_knowledge(state)
        
        assert result_state.get('current_step') == "extracting_knowledge"
        assert "knowledge_extraction" in result_state.get('completed_steps', [])
        assert len(result_state.get('extracted_knowledge', {}).get("entities", [])) > 0
        assert "knowledge_extraction" in result_state.get('step_results', {})
    
    @pytest.mark.asyncio
    async def test_question_generation_node(self, training_service):
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="我是工程师",
            conversation_stage="exploring"
        )
        
        result_state = training_service._generate_question(state)
        
        assert result_state.get('current_step') == "generating_question"
        assert "question_generation" in result_state.get('completed_steps', [])
        assert result_state.get('next_question') != ""
        assert "question_generation" in result_state.get('step_results', {})
    
    @pytest.mark.asyncio
    async def test_streaming_events_collection(self, training_service):
        print("\n========== 测试流式事件收集 ==========")
        events = []
        node_events = {"starts": [], "completes": []}
        
        print("开始处理对话，收集流式事件...")
        async for event in training_service.process_training_conversation(
            digital_human_id=1,
            user_message="我是一名Python开发者，帮我写一个冒泡函数",
            user_id=1
        ):
            event_obj = json.loads(event)
            events.append(event_obj)
            
            if event_obj.get('type') == 'node_start':
                node_events["starts"].append(event_obj.get('node'))
                print(f"🔵 [{event_obj.get('type')}] 节点: {event_obj.get('node')}")
            elif event_obj.get('type') == 'node_complete':
                node_events["completes"].append(event_obj.get('node'))
                print(f"🟢 [{event_obj.get('type')}] 节点: {event_obj.get('node')}")
            elif event_obj.get('type') == 'thinking':
                print(f"💭 [{event_obj.get('type')}] {event_obj.get('data', '')[:50]}...")
            else:
                data_str = str(event_obj.get('data', ''))[:100] if event_obj.get('data') else ''
                print(f"📝 [{event_obj.get('type')}]: {data_str}")
        
        print(f"\n总共收集到 {len(events)} 个事件")
        event_types = [e["type"] for e in events]
        print(f"事件类型列表: {event_types}")
        print(f"节点开始事件: {node_events['starts']}")
        print(f"节点完成事件: {node_events['completes']}")
        
        assert "user_message" in event_types
        assert any(t in event_types for t in ["thinking", "node_start", "node_complete"])
        
        if node_events["starts"]:
            print(f"✅ 检测到 {len(node_events['starts'])} 个节点开始事件")
            assert "intent_recognition" in ' '.join(node_events["starts"])
        
        if node_events["completes"]:
            print(f"✅ 检测到 {len(node_events['completes'])} 个节点完成事件")
            assert "intent_recognition" in ' '.join(node_events["completes"])
        
        user_msg_event = next(e for e in events if e["type"] == "user_message")
        assert "id" in user_msg_event
        print("=====================================\n")
    
    @pytest.mark.asyncio
    async def test_workflow_routing_logic(self, training_service):
        state1 = TrainingState(
            digital_human_id=1,
            user_id=1,
            should_extract=True,
            total_knowledge_points=0
        )
        assert training_service._route_after_intent(state1) == "extract"
        
        state2 = TrainingState(
            digital_human_id=1,
            user_id=1,
            should_extract=False,
            total_knowledge_points=10
        )
        assert training_service._route_after_intent(state2) == "analyze"
        
        state3 = TrainingState(
            digital_human_id=1,
            user_id=1,
            should_extract=False,
            total_knowledge_points=3
        )
        assert training_service._route_after_intent(state3) == "direct"
    
    @pytest.mark.asyncio
    async def test_fallback_to_ainvoke(self, training_service):
        with patch.object(training_service.training_graph, 'astream', side_effect=AttributeError("'async_generator' object has no attribute 'astream'")):
            events = []
            
            async for event in training_service.process_training_conversation(
                digital_human_id=1,
                user_message="测试异常处理",
                user_id=1
            ):
                events.append(json.loads(event))
            
            assert len(events) > 0
            assert any(e["type"] == "error" for e in events)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, training_service):
        training_service.training_message_repo.create_training_message.side_effect = Exception("数据库连接失败")
        
        events = []
        async for event in training_service.process_training_conversation(
            digital_human_id=1,
            user_message="测试错误",
            user_id=1
        ):
            events.append(json.loads(event))
        
        assert any(e["type"] == "error" for e in events)
        error_event = next(e for e in events if e["type"] == "error")
        assert "失败" in error_event["data"]
    
    @pytest.mark.asyncio
    async def test_message_persistence(self, training_service):
        events = []
        
        async for event in training_service.process_training_conversation(
            digital_human_id=1,
            user_message="测试消息持久化",
            user_id=1
        ):
            events.append(json.loads(event))
        
        # 检查 session repo 的 add_message_to_session 被调用
        assert training_service.training_session_repo.add_message_to_session.called
        
        save_calls = training_service.training_session_repo.add_message_to_session.call_args_list
        
        # 找到用户消息的调用
        user_message_calls = [call for call in save_calls if call.kwargs.get('role') == 'user']
        assert len(user_message_calls) > 0
        assert user_message_calls[0].kwargs['content'] == "测试消息持久化"
        
        # 检查 commit 被调用
        assert training_service.training_session_repo.commit.called
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, training_service):
        print("\n========== 测试完整工作流集成 ==========")
        collected_events = []
        
        user_message = """
        你好啊
        """
        print(f"📝 用户消息: {user_message[:100]}... (共{len(user_message)}字符)")
        print("\n🚀 执行工作流:")
        
        async for event in training_service.process_training_conversation(
            digital_human_id=1,
            user_message=user_message,
            user_id=1
        ):
            event_obj = json.loads(event)
            collected_events.append(event_obj)
            event_type = event_obj.get('type')
            
            if event_type == 'thinking':
                continue
            elif event_type == 'user_message':
                continue
            elif event_type == 'node_start':
                continue
            elif event_type == 'node_complete':
                node = event_obj.get('node', '')
                result = event_obj.get('result', {})
                
                if node == 'intent_recognition':
                    intent = result.get('intent', '未知')
                    stage = result.get('stage', '未知')
                    should_extract = result.get('should_extract', False)
                    print(f"  1️⃣ 意图识别 → {intent} (阶段: {stage}, 需要提取: {should_extract})")
                    
                elif node == 'knowledge_extraction':
                    entities_count = result.get('entities_count', 0)
                    relationships_count = result.get('relationships_count', 0)
                    print(f"  2️⃣ 知识提取 → {entities_count}个实体, {relationships_count}个关系")
                    
                elif node == 'context_analysis':
                    total_points = result.get('total_points', 0)
                    categories_count = result.get('categories_count', 0)
                    print(f"  3️⃣ 上下文分析 → {total_points}个知识点, {categories_count}个类别")
                    
                elif node == 'question_generation':
                    question = result.get('question', '')
                    if len(question) > 50:
                        question = question[:50] + '...'
                    print(f"  4️⃣ 问题生成 → \"{question}\"")
                    
                elif node == 'save_message':
                    print(f"  5️⃣ 消息保存 → 完成")
                    
            elif event_type == 'knowledge_extracted':
                entities = event_obj.get('data', [])
                print(f"\n  📊 【知识提取结果】")
                print(f"     提取到 {len(entities)} 个实体:")
                for entity in entities:
                    confidence = entity.get('confidence', 'N/A')
                    print(f"       • {entity.get('name')} - 类型: {entity.get('type')} (置信度: {confidence})")
                print()
                
            elif event_type == 'assistant_question':
                question = event_obj.get('data', '')
                if len(question) > 100:
                    question = question[:100] + '...'
                print(f"\n  🤖 助手回复: {question}")
            elif event_type == 'error':
                print(f"  ❌ 错误: {event_obj.get('data', '')}")
        
        thinking_count = len([e for e in collected_events if e.get('type') == 'thinking'])
        actual_events = len(collected_events) - thinking_count
        
        print(f"\n📊 执行统计:")
        print(f"  - 总事件数: {len(collected_events)} (过滤thinking后: {actual_events})")
        
        main_nodes = ['intent_recognition', 'knowledge_extraction', 'context_analysis', 
                      'question_generation', 'save_message']
        successful_nodes = []
        for node in main_nodes:
            node_events = [e for e in collected_events 
                          if e.get('node') == node and e.get('type') == 'node_complete']
            if node_events:
                successful_nodes.append(node)
        
        print(f"  - 执行节点: {len(successful_nodes)}/{len(main_nodes)}")
        if len(successful_nodes) == len(main_nodes):
            print(f"  - ✅ 全部节点成功执行")
        
        knowledge_events = [e for e in collected_events 
                           if e.get('type') == 'knowledge_extracted']
        if knowledge_events:
            entities = knowledge_events[0].get('data', [])
            print(f"\n📢 知识提取验证:")
            print(f"  - 实际提取实体数: {len(entities)}")
            assert len(entities) > 0, "应该提取到至少一个实体"
        
        event_types = [e["type"] for e in collected_events]
        assert "user_message" in event_types
        assert len(collected_events) >= 3
        
        user_msg_index = event_types.index("user_message")
        assert user_msg_index == 0
        print(f"\n✓ 用户消息是第一个事件")
        
        assistant_events = [e for e in collected_events if e["type"] == "assistant_question"]
        if assistant_events:
            assert "id" in assistant_events[0]
            assert assistant_events[0]["data"] != ""
            print(f"✓ 生成了助手问题: {assistant_events[0]['data'][:100]}...")
        print("=====================================\n")
    
    @pytest.mark.asyncio
    async def test_no_knowledge_extraction_scenario(self, training_service):
        state = {
            "digital_human_id": 1,
            "user_id": 1,
            "current_message": "你好",
            "messages": [],
            "extracted_knowledge": {},
            "knowledge_context": {},
            "next_question": "",
            "should_extract": False,
            "should_explore_deeper": False,
            "conversation_stage": "initial",
            "total_knowledge_points": 0,
            "categories": {},
            "current_step": "",
            "completed_steps": [],
            "step_results": {},
            "thinking_process": [],
            "events": []
        }
        
        result_state = training_service._recognize_intent(state)
        intent = result_state.get('step_results', {}).get('intent_recognition', {}).get('intent', '未知')
        print(f"AI 识别结果: intent={intent}, should_extract={result_state.get('should_extract')}")
        
        result_state = await training_service._extract_knowledge(result_state)
        print(f"抽取结果: {result_state.get('extracted_knowledge')}")
    
    @pytest.mark.asyncio
    async def test_graph_storage_operations(self, training_service):
        entity = {
            "name": "测试实体",
            "type": "person",
            "types": ["person", "professional"],
            "confidence": 0.9,
            "properties": {"role": "engineer"}
        }
        
        result = await training_service.graph_service.store_digital_human_entity(1, entity)
        assert result is True
        
        relationship = {
            "source": "实体1",
            "target": "实体2",
            "relation_type": "关系类型",
            "confidence": 0.8,
            "properties": {}
        }
        
        result = await training_service.graph_service.store_digital_human_relationship(1, relationship)
        assert result is True
        
        print("✅ 图存储操作完成（通过 GraphService）")
    
    @pytest.mark.asyncio
    async def test_generate_graph_visualization(self):
        print("\n========== 生成工作流图可视化 ==========")
        
        from app.services.digital_human_training_service import DigitalHumanTrainingService
        
        service = DigitalHumanTrainingService(
            training_message_repo=None,
            training_session_repo=None,
            knowledge_extractor=None,
            graph_service=None
        )
        
        print("\n📸 尝试生成图片...")
        saved_path = service.save_graph_visualization()
        if saved_path:
            print(f"✅ 图已保存到: {saved_path}")
        
        print("\n💡 提示: 可以打开 graph_visualizations/training_graph.mmd 查看 Mermaid 图")
        print("     或访问 https://mermaid.live 粘贴内容查看流程图")
        
        print("\n✨ 工作流图可视化测试完成！")
        print("=====================================\n")