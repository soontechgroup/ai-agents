# LangGraph 有状态工作流框架

## 📚 使用说明

项目使用 LangGraph 构建有状态的 AI 工作流，支持复杂的对话管理和多步骤处理。

## 🛠 框架配置

### 安装依赖
```bash
pip install langgraph
```

### 基本配置
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict

# 定义状态结构
class WorkflowState(TypedDict):
    messages: list
    current_step: str
    result: str

# 创建工作流
workflow = StateGraph(WorkflowState)

# 添加节点
workflow.add_node("process", process_node)
workflow.add_node("analyze", analyze_node)

# 设置流程
workflow.set_entry_point("process")
workflow.add_edge("process", "analyze")
workflow.add_edge("analyze", END)

# 编译工作流
app = workflow.compile()
```


## 💻 项目应用

### 数字人训练工作流
```python
# app/services/digital_human_training_service.py
class DigitalHumanTrainingFlow:
    def __init__(self, llm, memory_service):
        self.llm = llm
        self.memory_service = memory_service
        self.checkpointer = SqliteSaver.from_conn_string("sqlite:///training.db")

    class TrainingState(TypedDict):
        thread_id: str
        user_message: str
        intent: str
        memory_results: list
        response: str

    def build_workflow(self) -> StateGraph:
        workflow = StateGraph(self.TrainingState)

        # 添加节点
        workflow.add_node("message_analysis", self.analyze_message)
        workflow.add_node("intent_recognition", self.recognize_intent)
        workflow.add_node("memory_search", self.search_memory)
        workflow.add_node("response_generation", self.generate_response)
        workflow.add_node("memory_storage", self.store_memory)

        # 设置流程
        workflow.set_entry_point("message_analysis")
        workflow.add_edge("message_analysis", "intent_recognition")
        workflow.add_edge("intent_recognition", "memory_search")
        workflow.add_edge("memory_search", "response_generation")
        workflow.add_edge("response_generation", "memory_storage")
        workflow.add_edge("memory_storage", END)

        return workflow.compile(checkpointer=self.checkpointer)
```

### 流式响应集成
```python
# app/api/v1/endpoints/conversations.py
class StreamingConversationAPI:
    async def stream_conversation(self, thread_id: str, message: str):
        async def generate_stream():
            initial_state = {
                "thread_id": thread_id,
                "user_message": message,
                "intent": "",
                "memory_results": [],
                "response": ""
            }

            config = {"configurable": {"thread_id": thread_id}}

            async for event in self.workflow.astream(initial_state, config):
                if "response_generation" in event:
                    yield f"data: {json.dumps(event['response_generation'])}\n\n"

        return StreamingResponse(generate_stream(), media_type="text/plain")
```

### 状态持久化
```python
# app/core/checkpointer.py
class MySQLCheckpointer:
    def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        thread_id = config.get("configurable", {}).get("thread_id")

        # 从数据库加载历史对话状态
        latest_checkpoint = db.query(ConversationCheckpoint).filter(
            ConversationCheckpoint.thread_id == thread_id
        ).order_by(desc(ConversationCheckpoint.version)).first()

        # 如果没有checkpoint，从Message表加载历史消息
        if not latest_checkpoint:
            messages = db.query(Message).filter(
                Message.user_id == user_id,
                Message.digital_human_id == digital_human_id
            ).order_by(Message.created_at).limit(50).all()
```

LangGraph 为项目提供了有状态的工作流管理能力，支持复杂的 AI 对话处理和多步骤任务编排。