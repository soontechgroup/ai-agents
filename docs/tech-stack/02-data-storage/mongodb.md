# MongoDB - 面向文档的NoSQL数据库

## 📚 使用说明

项目使用 MongoDB 7.0 作为文档数据库，存储灵活的非结构化数据。

## 🛠 数据库配置

### Docker 启动
```bash
# 启动 MongoDB 服务
docker-compose up -d mongodb

# 查看运行状态
docker-compose ps
```

### 连接信息
- **主机**: localhost
- **端口**: 27018
- **用户名**: admin
- **密码**: password123
- **数据库**: ai_agents

### 数据库连接
```python
# MongoDB 连接配置
MONGODB_URL = "mongodb://admin:password123@localhost:27018/?authSource=admin"

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# 异步客户端
client = AsyncIOMotorClient(MONGODB_URL)
database = client.ai_agents
```

### Python 使用示例
```python
# 基本使用
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://admin:password123@localhost:27018/")
db = client.ai_agents

async def get_collection():
    collection = db.conversations
    return collection

# 基础操作
async def create_document(data: dict):
    collection = await get_collection()
    result = await collection.insert_one(data)
    return result.inserted_id
```

MongoDB 为项目提供灵活的文档存储，适合存储复杂的 JSON 结构数据。