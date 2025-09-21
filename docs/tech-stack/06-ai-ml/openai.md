# OpenAI GPT API

## 📚 使用说明

项目使用 OpenAI GPT 模型作为核心 AI 引擎，提供智能对话和文本生成能力。

## 🛠 框架配置

### 安装依赖
```bash
pip install openai
```

### 基本配置
```python
import openai
from openai import OpenAI

# 初始化客户端
client = OpenAI(api_key="your-api-key")

# 基本调用
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是一个专业的AI助手"},
        {"role": "user", "content": "用户消息"}
    ],
    temperature=0.3,
    max_tokens=1000
)

assistant_message = response.choices[0].message.content
```


## 💻 项目应用

### 数字人训练服务
```python
# app/services/digital_human_training_service.py
class DigitalHumanTrainingService:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.3
        )

    def _recognize_intent(self, state: TrainingState) -> Dict[str, Any]:
        prompt = f"""
        分析用户消息的意图：
        当前用户消息: {state['current_message']}

        返回JSON格式：
        {{
            "intent": "information_sharing/question_asking/greeting",
            "stage": "initial/exploring/deepening"
        }}
        """

        response = self.llm.invoke([SystemMessage(content=prompt)])
        return json.loads(response.content)
```

### 知识抽取服务
```python
# app/services/knowledge_extractor.py
class KnowledgeExtractor:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    async def extract_entities_and_relations(self, text: str):
        prompt = f"""
        从以下文本中提取实体和关系：
        文本：{text}

        请返回JSON格式的结果
        """

        response = self.llm.invoke([SystemMessage(content=prompt)])
        return json.loads(response.content)
```

### 流式对话服务
```python
# app/services/langgraph_service.py
class LangGraphService:
    def chat_stream(self, message: str, config: dict):
        prompt = self._build_chat_prompt(message, config)

        for chunk in self.llm.stream(prompt):
            if chunk.content:
                yield chunk.content
```


OpenAI GPT 为项目提供了核心的 AI 能力，支持智能对话、意图识别和知识抽取功能。