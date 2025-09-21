# ChromaDB 向量数据库

## 📚 使用说明

项目使用 ChromaDB 作为向量数据库，用于存储和检索文档的语义向量。

## 🛠 数据库配置

### Docker 启动
```bash
# 启动 ChromaDB 服务
docker-compose up -d chromadb

# 查看运行状态
docker-compose ps
```

### 连接信息
- **主机**: localhost
- **端口**: 8000
- **数据存储**: ./data/chroma_db

### 数据库连接
```python
# ChromaDB 连接配置
import chromadb
from chromadb.config import Settings

# 持久化客户端
client = chromadb.PersistentClient(
    path="./data/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)
```

### Python 使用示例
```python
# 基本使用
from app.repositories.chroma_repository import ChromaRepository

# 初始化仓储
chroma_repo = ChromaRepository(persist_directory="./data/chroma_db")

# 创建集合
collection = chroma_repo.get_or_create_collection("test_collection")

# 添加文档
chroma_repo.add_documents(
    collection_name="test_collection",
    documents=["这是一个测试文档"],
    ids=["doc1"]
)
```

ChromaDB 为项目提供高效的向量存储和语义搜索功能。