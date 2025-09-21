# Neo4j 图数据库

## 📚 使用说明

项目使用 Neo4j 5.15 作为图数据库，存储知识图谱和实体关系数据。

## 🛠 数据库配置

### Docker 启动
```bash
# 启动 Neo4j 服务
docker-compose up -d neo4j

# 查看运行状态
docker-compose ps
```

### 连接信息
- **Web 界面**: http://localhost:7474
- **Bolt 协议**: bolt://localhost:7687
- **用户名**: neo4j
- **密码**: password123
- **数据库**: neo4j

### 数据库连接
```python
# Neo4j 连接配置
from neomodel import config as neomodel_config

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "password123"

# 设置连接
connection_url = f"bolt://{NEO4J_USERNAME}:{NEO4J_PASSWORD}@localhost:7687"
neomodel_config.DATABASE_URL = connection_url
```

### Python 使用示例
```python
# 基本使用
from neomodel import db
from app.models.neomodel.entity import ExtractedEntity

# 直接 Cypher 查询
results, meta = db.cypher_query(
    "MATCH (e:ExtractedEntity) RETURN e.name LIMIT 5"
)

# 使用 Neomodel ORM
entity = ExtractedEntity(
    name="Python",
    entity_type="Technology",
    description="编程语言"
).save()
```

Neo4j 为项目提供强大的图数据存储和关系查询能力。