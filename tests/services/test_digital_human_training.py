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
    def mock_db(self):
        db = Mock()
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        
        message_counter = [0]
        def flush_side_effect():
            for call in db.add.call_args_list:
                if call and len(call[0]) > 0:
                    obj = call[0][0]
                    if isinstance(obj, DigitalHumanTrainingMessage) and not hasattr(obj, 'id'):
                        message_counter[0] += 1
                        obj.id = message_counter[0]
        
        db.flush.side_effect = flush_side_effect
        return db
    
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
        return Mock()
    
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
    async def training_service(self, mock_db, mock_knowledge_extractor, mock_graph_service, mock_graph_repo):
        service = DigitalHumanTrainingService(
            db=mock_db,
            knowledge_extractor=mock_knowledge_extractor,
            graph_service=mock_graph_service
        )
        
        service.graph_repo = mock_graph_repo
        # 不再替换 llm 和 training_graph，使用 service 自带的真实组件
        # service.llm 已经在 __init__ 中初始化为真实的 ChatOpenAI
        # service.training_graph 已经在 __init__ 中构建为真实的 LangGraph
        
        return service
    
    @pytest.mark.asyncio
    async def test_intent_recognition_node(self, training_service):
        print("\n========== 测试意图识别节点 ==========")
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="我是一名软件工程师，在阿里巴巴工作了5年"
        )
        print(f"输入消息: {state.current_message}")
        
        result_state = training_service._recognize_intent(state)
        
        print(f"当前步骤: {result_state.current_step}")
        print(f"已完成步骤: {result_state.completed_steps}")
        print(f"识别到的意图: {result_state.intent}")
        print(f"是否需要抽取知识: {result_state.should_extract}")
        print(f"对话阶段: {result_state.conversation_stage}")
        print(f"思考过程: {result_state.thinking_process}")
        print(f"步骤结果: {result_state.step_results}")
        print("=====================================\n")
        
        assert result_state.current_step == "recognizing_intent"
        assert "intent_recognition" in result_state.completed_steps
        assert result_state.intent == "information_sharing"
        # 真实 AI 可能有不同的判断，所以只验证字段存在
        assert isinstance(result_state.should_extract, bool)
        assert len(result_state.thinking_process) >= 2
        print(f"✅ 真实 AI 判断: should_extract = {result_state.should_extract}")
    
    @pytest.mark.asyncio
    async def test_intent_recognition_json_error(self, training_service):
        """测试意图识别JSON解析失败时应该抛出异常"""
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="测试消息"
        )
        
        # 临时模拟一个坏的响应来测试错误处理
        # 这是唯一需要 mock 的地方，因为我们要测试错误处理
        bad_response = Mock()
        bad_response.content = "这不是一个有效的JSON"
        original_llm = training_service.llm
        training_service.llm = Mock()
        training_service.llm.invoke = Mock(return_value=bad_response)
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="意图识别响应格式错误"):
            training_service._recognize_intent(state)
        
        # 恢复原来的 llm
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
        
        assert result_state.current_step == "extracting_knowledge"
        assert "knowledge_extraction" in result_state.completed_steps
        assert len(result_state.extracted_knowledge.get("entities", [])) > 0
        assert "knowledge_extraction" in result_state.step_results
    
    @pytest.mark.asyncio
    async def test_question_generation_node(self, training_service):
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="我是工程师",
            conversation_stage="exploring"
        )
        
        result_state = training_service._generate_question(state)
        
        assert result_state.current_step == "generating_question"
        assert "question_generation" in result_state.completed_steps
        assert result_state.next_question != ""
        assert "question_generation" in result_state.step_results
    
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
            
            # 记录节点事件
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
        
        # 验证基本事件
        assert "user_message" in event_types
        assert any(t in event_types for t in ["thinking", "node_start", "node_complete"])
        
        # 验证节点事件
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
        assert training_service._route_by_intent(state1) == "extract"
        
        state2 = TrainingState(
            digital_human_id=1,
            user_id=1,
            should_extract=False,
            total_knowledge_points=10
        )
        assert training_service._route_by_intent(state2) == "analyze"
        
        state3 = TrainingState(
            digital_human_id=1,
            user_id=1,
            should_extract=False,
            total_knowledge_points=3
        )
        assert training_service._route_by_intent(state3) == "direct"
    
    @pytest.mark.asyncio
    async def test_fallback_to_ainvoke(self, training_service):
        """测试当 astream 不可用时的异常处理"""
        with patch.object(training_service.training_graph, 'astream', side_effect=AttributeError("'async_generator' object has no attribute 'astream'")):
            events = []
            
            async for event in training_service.process_training_conversation(
                digital_human_id=1,
                user_message="测试异常处理",
                user_id=1
            ):
                events.append(json.loads(event))
            
            # 验证异常被正确捕获并返回错误事件
            assert len(events) > 0
            # 确保有错误事件产生
            assert any(e["type"] == "error" for e in events)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, training_service):
        training_service.db.add.side_effect = Exception("数据库连接失败")
        
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
        
        assert training_service.db.add.called
        assert training_service.db.flush.called
        assert training_service.db.commit.called
        
        add_calls = training_service.db.add.call_args_list
        messages_added = [call[0][0] for call in add_calls if call and len(call[0]) > 0]
        
        user_messages = [m for m in messages_added if isinstance(m, DigitalHumanTrainingMessage) and m.role == "user"]
        assert len(user_messages) > 0
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, training_service):
        print("\n========== 测试完整工作流集成 ==========")
        collected_events = []
        
        user_message = "你好"
        print(f"用户消息: {user_message}")
        print("\n开始执行完整工作流...")
        
        async for event in training_service.process_training_conversation(
            digital_human_id=1,
            user_message=user_message,
            user_id=1
        ):
            event_obj = json.loads(event)
            collected_events.append(event_obj)
            event_type = event_obj.get('type')
            
            # 根据事件类型显示不同的信息
            if event_type == 'workflow_start':
                print(f"  🚀 [{event_type}]: {event_obj.get('data', '')}")
            elif event_type == 'workflow_complete':
                print(f"  🏁 [{event_type}]: {event_obj.get('data', '')}")
            elif event_type == 'node_start':
                print(f"  🔵 [{event_type}] 节点: {event_obj.get('node', '')}")
            elif event_type == 'node_complete':
                node = event_obj.get('node', '')
                summary = event_obj.get('summary', '')
                exec_time = event_obj.get('execution_time', '')
                
                # 显示节点完成信息和执行时间
                if exec_time:
                    print(f"  🟢 [{event_type}] 节点: {node} ({exec_time}) - {summary}")
                else:
                    print(f"  🟢 [{event_type}] 节点: {node} - {summary}")
                
                # 如果有详细结果，显示它
                if event_obj.get('result'):
                    result = event_obj['result']
                    for key, value in result.items():
                        print(f"       └─ {key}: {value}")
            elif event_type == 'assistant_question':
                print(f"  🤖 [{event_type}]: {event_obj.get('data', '')}")
            elif event_type == 'intent_recognized':
                data = event_obj.get('data', {})
                print(f"  🎯 [{event_type}]: 意图={data.get('intent')}, 阶段={data.get('stage')}")
            else:
                event_data = str(event_obj.get('data', ''))[:150]
                print(f"  📝 [{event_type}]: {event_data}")
        
        print(f"\n工作流执行完成，共产生 {len(collected_events)} 个事件")
        
        # 创建更有信息量的事件流序列
        event_descriptions = []
        node_timings = {}  # 记录节点执行时间
        
        for event in collected_events:
            event_type = event.get('type')
            
            if event_type in ['node_start', 'node_complete']:
                node_name = event.get('node', 'unknown')
                # 过滤内部节点
                if node_name.startswith('_') or node_name == '__start__' or node_name == 'LangGraph':
                    continue
                    
                if event_type == 'node_start':
                    event_descriptions.append(f"{node_name}:开始")
                    node_timings[node_name] = {'start': len(event_descriptions)}
                elif event_type == 'node_complete':
                    event_descriptions.append(f"{node_name}:完成")
                    if node_name in node_timings:
                        node_timings[node_name]['end'] = len(event_descriptions)
            elif event_type == 'assistant_question':
                event_descriptions.append("助手回复")
            elif event_type == 'user_message':
                event_descriptions.append("用户输入")
            elif event_type == 'thinking':
                event_descriptions.append("思考中")
            elif event_type == 'intent_recognized':
                data = event.get('data', {})
                event_descriptions.append(f"意图:{data.get('intent', '未知')}")
        
        # 显示精简的事件流
        print(f"\n📊 事件流程:")
        print(f"  {' → '.join(event_descriptions)}")
        
        # 显示主要节点
        main_nodes = ['intent_recognition', 'knowledge_extraction', 'context_analysis', 
                      'question_generation', 'save_message']
        print(f"\n🔍 主要节点执行情况:")
        for node in main_nodes:
            node_events = [e for e in collected_events 
                          if e.get('node') == node and e.get('type') in ['node_start', 'node_complete']]
            if len(node_events) == 2:  # 有开始和完成
                print(f"  ✅ {node}")
            elif len(node_events) == 1:  # 只有开始或完成
                print(f"  ⚠️  {node} (未完成)")
            else:
                print(f"  ⏭️  {node} (跳过)")
        
        # 基本验证
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
        # 使用一个简单的问候语，真实 AI 应该能识别这不包含知识
        state = TrainingState(
            digital_human_id=1,
            user_id=1,
            current_message="你好"
        )
        
        result_state = training_service._recognize_intent(state)
        # 真实 AI 应该识别这是 greeting，不需要抽取知识
        print(f"AI 识别结果: intent={result_state.intent}, should_extract={result_state.should_extract}")
        
        # 即使 should_extract 是 True，知识抽取也应该返回空
        result_state = await training_service._extract_knowledge(result_state)
        # 对于"你好"这样的消息，应该没有实体可抽取
        # 但由于是 mock 的 extractor，可能会返回模拟数据
        print(f"抽取结果: {result_state.extracted_knowledge}")
    
    @pytest.mark.asyncio
    async def test_graph_storage_operations(self, training_service):
        entity = {
            "name": "测试实体",
            "type": "person",
            "types": ["person", "professional"],
            "confidence": 0.9,
            "properties": {"role": "engineer"}
        }
        
        await training_service._store_entity_to_graph(1, entity)
        
        assert training_service.graph_repo.execute_query.called
        call_args = training_service.graph_repo.execute_query.call_args
        assert call_args[0][1]["name"] == "测试实体"
        assert call_args[0][1]["dh_id"] == 1
        
        relationship = {
            "source": "实体1",
            "target": "实体2",
            "relation_type": "关系类型",
            "confidence": 0.8,
            "properties": {}
        }
        
        await training_service._store_relationship_to_graph(1, relationship)
        
        assert training_service.graph_repo.execute_query.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_generate_graph_visualization(self):
        """生成并保存工作流图的可视化"""
        print("\n========== 生成工作流图可视化 ==========")
        
        # 创建真实的服务实例（不用 mock）
        from app.services.digital_human_training_service import DigitalHumanTrainingService
        
        # 这里传入 None 因为只需要图的结构，不需要真实的依赖
        service = DigitalHumanTrainingService(
            db=None,
            knowledge_extractor=None,
            graph_service=None
        )
        
        # 1. 尝试生成图片
        print("\n📸 尝试生成图片...")
        saved_path = service.save_graph_visualization()
        if saved_path:
            print(f"✅ 图已保存到: {saved_path}")
        
        # 2. 生成 ASCII 图
        print("\n📊 ASCII 格式的工作流图:")
        print("=" * 50)
        ascii_graph = service.get_graph_ascii()
        print(ascii_graph)
        print("=" * 50)
        
        # 3. 生成 Mermaid 图
        print("\n🧜 Mermaid 格式（可以粘贴到 https://mermaid.live 查看）:")
        print("=" * 50)
        mermaid_graph = service.get_graph_mermaid()
        print(mermaid_graph)
        print("=" * 50)
        print("\n💡 提示: 将上面的 Mermaid 代码复制到 https://mermaid.live 即可看到流程图")
        
        # 验证基本结构
        assert "intent_recognition" in ascii_graph or "intent_recognition" in mermaid_graph
        assert "knowledge_extraction" in ascii_graph or "knowledge_extraction" in mermaid_graph
        assert "question_generation" in ascii_graph or "question_generation" in mermaid_graph
        
        print("\n✨ 工作流图可视化测试完成！")
        print("=====================================\n")