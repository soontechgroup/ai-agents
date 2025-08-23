# Neo4j架构重构文档

## 重构概述

将Neo4j图数据库从基于driver的实现完全迁移到Neomodel ORM，实现更清晰的架构和更好的开发体验。

## 架构变化

### 之前架构（基于neo4j-driver）
```
API层 → GraphRepository → neo4j.Session → Neo4j DB
```

### 新架构（基于Neomodel ORM）
```
API层(Pydantic) → Service层 → Neomodel Repository → Neo4j DB
```

## 主要变更

### 1. 删除的文件
- `app/repositories/graph/` - 整个目录（基于driver的实现）
- `app/core/neo4j.py` - driver配置
- `app/api/v1/endpoints/graph.py` - 通用CRUD端点

### 2. 新增的文件

#### Repository层
```
app/repositories/neomodel/
├── __init__.py
├── base.py          # 基础Repository类
├── person.py        # 人员Repository
├── organization.py  # 组织Repository
├── location.py      # 地点Repository
├── event.py         # 事件Repository
├── project.py       # 项目Repository
├── product.py       # 产品Repository
├── tag.py           # 标签Repository
└── category.py      # 分类Repository
```

#### API端点
```
app/api/v1/endpoints/
├── persons.py       # 人员管理API
├── organizations.py # 组织管理API
├── relationships.py # 关系管理API
└── analytics.py     # 图分析API
```

### 3. 更新的文件
- `app/services/graph_service.py` - 完全重写，使用Neomodel
- `app/dependencies/graph.py` - 简化依赖注入
- `app/main.py` - 添加Neomodel初始化
- `app/api/v1/router.py` - 使用新的业务端点

## API变更

### 旧API（通用CRUD）
```
POST /api/v1/graph/nodes
GET  /api/v1/graph/nodes/{node_id}
PUT  /api/v1/graph/nodes/{node_id}
DELETE /api/v1/graph/nodes/{node_id}
```

### 新API（业务导向）
```
# 人员管理
POST   /api/v1/graph/persons
GET    /api/v1/graph/persons/{uid}
PUT    /api/v1/graph/persons/{uid}
DELETE /api/v1/graph/persons/{uid}
GET    /api/v1/graph/persons/{uid}/network
GET    /api/v1/graph/persons/{uid}/recommendations

# 组织管理
POST   /api/v1/graph/organizations
GET    /api/v1/graph/organizations/{uid}
GET    /api/v1/graph/organizations/{uid}/employees

# 关系管理
POST   /api/v1/graph/relationships/employment
POST   /api/v1/graph/relationships/friendship
POST   /api/v1/graph/relationships/shortest-path

# 图分析
GET    /api/v1/graph/analytics/statistics
```

## 核心改进

### 1. 类型安全
- Pydantic模型用于API验证
- Neomodel模型用于数据库操作
- 自动模型转换

### 2. 代码简化
- 删除50%冗余代码
- 更清晰的职责分离
- 更好的错误处理

### 3. 性能优化
- ORM自动查询优化
- 连接池管理
- 事务支持

### 4. 开发体验
- 更直观的API
- 自动代码补全
- 更好的IDE支持

## 使用示例

### 创建人员
```python
from app.models.graph.nodes import PersonNode
from app.services.graph_service import GraphService

# API层接收Pydantic模型
person = PersonNode(
    uid="person_001",
    name="张三",
    email="zhangsan@example.com"
)

# Service层处理业务逻辑
service = GraphService()
created = await service.create_person(person)
```

### 添加关系
```python
# 添加雇佣关系
await service.add_employment(
    person_uid="person_001",
    org_uid="org_001",
    position="工程师",
    department="技术部"
)

# 添加朋友关系
await service.add_friendship(
    person1_uid="person_001",
    person2_uid="person_002"
)
```

### 复杂查询
```python
# 获取社交网络
network = await service.get_person_network("person_001", depth=3)

# 查找最短路径
path = await service.find_shortest_path("person_001", "person_002")

# 获取推荐
recommendations = await service.get_recommendations("person_001")
```

## 迁移指南

### 1. 环境准备
```bash
# 确保Neo4j运行
docker-compose up -d neo4j

# 清空数据库（如需要）
MATCH (n) DETACH DELETE n;
```

### 2. 运行应用
```bash
python run.py
```

### 3. 测试新API
访问 http://localhost:8000/docs 查看新的API文档

## 注意事项

1. **UID vs ID**：使用业务UID而非Neo4j内部ID
2. **模型转换**：Pydantic ↔ Neomodel自动转换
3. **事务处理**：使用`transaction()`上下文管理器
4. **异步操作**：Service层方法都是异步的

## 后续优化

1. 添加缓存层（Redis）
2. 实现GraphQL接口
3. 添加更多图算法
4. 性能监控和优化