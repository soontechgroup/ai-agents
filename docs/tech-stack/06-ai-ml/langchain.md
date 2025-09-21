# LangChain LLM应用框架

## 📚 使用说明

项目使用 LangChain 作为 LLM 应用开发框架，提供模块化的组件来构建智能对话系统。

## 🛠 框架配置

### 安装依赖
```bash
pip install langchain langchain-openai
```

### 基本配置
```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

# LLM初始化
llm = ChatOpenAI(
    api_key="your-api-key",
    model="gpt-4o-mini",
    temperature=0.3
)

# Prompt模板
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="你是一个专业的AI助手"),
    ("user", "{input}")
])

# 调用
response = llm.invoke(prompt.format_messages(input="用户消息"))
```

## 💻 项目应用

### LLM服务初始化
```python
# app/services/digital_human_training_service.py
class DigitalHumanTrainingService:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.3
        )
```

### 意图识别
```python
def _recognize_intent(self, state: TrainingState) -> Dict[str, Any]:
    prompt = f"""
    分析用户消息的意图和内容类型：
    当前用户消息: {state['current_message']}

    返回JSON格式：
    {{
        "intent": "information_sharing/question_asking/greeting/other",
        "stage": "initial/exploring/deepening/concluding"
    }}
    """

    response = self.llm.invoke([SystemMessage(content=prompt)])
    return json.loads(response.content)
```

### 消息系统集成
```python
# app/core/messages.py
from langchain_core.messages import BaseMessage

class UserMessage(BaseMessage):
    type: Literal["user"] = "user"

class AssistantMessage(BaseMessage):
    type: Literal["assistant"] = "assistant"
```

### 流式处理
```python
# app/services/langgraph_service.py
class LangGraphService:
    def chat_stream(self, message: str, config: dict):
        prompt = self._build_chat_prompt(message, config)

        for chunk in self.llm.stream(prompt):
            if chunk.content:
                yield chunk.content
```

### 知识抽取集成
```python
# app/services/knowledge_extractor.py
class KnowledgeExtractor:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    async def extract_entities_and_relations(self, text: str):
        prompt = f"从以下文本中提取实体和关系：\n{text}"
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return json.loads(response.content)
```

LangChain 为项目提供了模块化的 LLM 应用开发基础，支持智能对话和知识处理。