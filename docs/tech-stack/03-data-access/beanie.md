# Beanie MongoDB ODM框架

## 📚 使用说明

项目使用 Beanie 作为 MongoDB 的 ODM（对象文档映射）框架，提供类型安全的异步数据操作。

## 🛠 框架配置

### 安装依赖
```bash
pip install beanie motor
```

### 初始化配置
```python
# 数据库连接和初始化
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

async def init_mongodb():
    client = AsyncIOMotorClient("mongodb://admin:password123@localhost:27018/")
    await init_beanie(
        database=client.ai_agents,
        document_models=[Conversation]
    )
```

### 基本使用示例
```python
# 文档模型定义
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Conversation(Document):
    thread_id: Indexed(str, unique=True)
    user_id: int
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversations"

# 基本操作
async def create_conversation(thread_id: str, user_id: int):
    conversation = Conversation(thread_id=thread_id, user_id=user_id)
    await conversation.insert()
    return conversation

async def get_conversation(thread_id: str):
    return await Conversation.find_one(Conversation.thread_id == thread_id)
```

Beanie 为项目提供类型安全的 MongoDB 异步操作，基于 Pydantic 进行数据验证。