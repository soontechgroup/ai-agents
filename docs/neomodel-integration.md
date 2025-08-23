# Neomodel ORM 集成指南

## 概述

本项目实现了基于Neomodel ORM的Neo4j图数据库集成，提供了一个混合架构：
- **Pydantic模型**：用于API层的数据验证和文档生成
- **Neomodel模型**：用于数据层的ORM操作
- **模型转换器**：实现两种模型之间的无缝转换

## 架构设计

```
┌─────────────────┐
│   API 层        │
│  (Pydantic)     │
└────────┬────────┘
         │
    ┌────▼────┐
    │ 转换器   │
    └────┬────┘
         │
┌────────▼────────┐
│  Repository层   │
│   (Neomodel)    │
└────────┬────────┘
         │
┌────────▼────────┐
│    Neo4j DB     │
└─────────────────┘
```

## 核心组件

### 1. Pydantic模型 (`app/models/graph/`)

用于API验证和文档生成：

```python
from app.models.graph.nodes.person import PersonNode

# 创建Pydantic模型实例
person = PersonNode(
    uid="person_001",
    name="张三",
    email="zhangsan@example.com"
)

# 转换为Neomodel
neomodel_person = person.to_neomodel()
```

### 2. Neomodel模型 (`app/models/neomodel/`)

用于数据库ORM操作：

```python
from app.models.neomodel.nodes import Person

# 创建Neomodel实例
person = Person(
    uid="person_001",
    name="张三",
    email="zhangsan@example.com"
)
person.save()

# 转换为Pydantic
pydantic_person = PersonNode.from_neomodel(person)
```

### 3. 模型转换器 (`app/models/converters/`)

自动处理模型转换：

```python
from app.models.converters.graph_converter import GraphModelConverter

# Pydantic → Neomodel
neomodel_obj = GraphModelConverter.pydantic_to_neomodel(pydantic_obj)

# Neomodel → Pydantic  
pydantic_obj = GraphModelConverter.neomodel_to_pydantic(neomodel_obj)
```

### 4. Repository层 (`app/repositories/neomodel_repository.py`)

提供高级数据访问接口：

```python
from app.repositories.neomodel_repository import PersonRepository

repo = PersonRepository()

# CRUD操作
person = repo.create(uid="001", name="张三")
person = repo.find_by_uid("001")
person = repo.update("001", age=30)
success = repo.delete("001")

# 高级查询
results = repo.search("张", ["name", "bio"])
page = repo.paginate(page=1, per_page=10)
```

## 快速开始

### 1. 初始化连接

```python
from app.core.neomodel_config import setup_neomodel

# 在应用启动时调用
setup_neomodel()
```

### 2. 基本CRUD操作

```python
from app.repositories.neomodel_repository import PersonRepository

# 初始化仓储
repo = PersonRepository()

# 创建
person = repo.create(
    uid="person_001",
    name="张三",
    email="zhangsan@example.com",
    skills=["Python", "Neo4j"]
)

# 查询
person = repo.find_by_uid("person_001")
persons = repo.find_all(occupation="工程师")

# 更新
updated = repo.update("person_001", age=30)

# 删除
deleted = repo.delete("person_001")
```

### 3. 关系管理

```python
# 创建节点
person = person_repo.create(uid="p1", name="张三")
org = org_repo.create(uid="o1", name="公司")

# 建立关系
person.works_at.connect(org, {
    'position': 'CTO',
    'start_date': datetime.now()
})

# 查询关系
employees = org.employees.all()
workplace = person.works_at.single()
```

### 4. 事务处理

```python
from app.core.neomodel_config import transaction

with transaction():
    person1 = repo.create(uid="p1", name="张三")
    person2 = repo.create(uid="p2", name="李四")
    person1.knows.connect(person2)
    # 如果出错，所有操作都会回滚
```

## 模型定义

### Neomodel节点示例

```python
from neomodel import StructuredNode, StringProperty, RelationshipTo
from app.models.neomodel.base import BaseNode

class Person(BaseNode):
    # 属性
    name = StringProperty(required=True)
    email = EmailProperty(unique_index=True)
    
    # 关系
    friends = Relationship('Person', 'FRIEND_OF')
    works_at = RelationshipTo('Organization', 'WORKS_AT')
```

### Pydantic模型示例

```python
from pydantic import Field
from app.models.graph.base import Node

class PersonNode(Node):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)
```

## 高级特性

### 1. 批量操作

```python
# 批量创建
items = [{"uid": f"p{i}", "name": f"用户{i}"} for i in range(100)]
created = repo.bulk_create(items)

# 批量删除
deleted_count = repo.delete_all(age__gt=60)
```

### 2. 分页查询

```python
result = repo.paginate(
    page=1,
    per_page=20,
    occupation="工程师"
)

print(f"总数: {result['total']}")
print(f"页数: {result['pages']}")
for item in result['items']:
    print(item.name)
```

### 3. 复杂查询

```python
# 使用Cypher查询
from neomodel import db

query = """
    MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
    WHERE o.industry = $industry
    RETURN p.name, o.name
"""
results, _ = db.cypher_query(query, {"industry": "互联网"})
```

### 4. 模型转换

```python
# API接收Pydantic模型
@router.post("/person")
async def create_person(person: PersonNode):
    # 转换为Neomodel进行存储
    neomodel_person = person.to_neomodel()
    neomodel_person.save()
    
    # 返回Pydantic模型
    return PersonNode.from_neomodel(neomodel_person)
```

## 注意事项

1. **连接管理**：确保在应用启动时调用`setup_neomodel()`
2. **事务处理**：批量操作建议使用事务包装
3. **索引创建**：Neomodel会自动创建定义的索引
4. **类型转换**：日期时间类型会自动在字符串和对象间转换
5. **关系属性**：关系可以包含属性，通过`connect()`方法传递

## 性能优化

1. **使用索引**：为常用查询字段添加索引
2. **批量操作**：使用批量方法而不是循环单个操作
3. **懒加载**：关系默认懒加载，需要时才查询
4. **连接池**：Neo4j驱动自动管理连接池

## 故障排除

### 连接失败

```python
# 检查配置
print(settings.NEO4J_URI)
print(settings.NEO4J_USERNAME)

# 测试连接
from neomodel import db
db.cypher_query("RETURN 1")
```

### 模型不匹配

```python
# 确保Pydantic和Neomodel模型字段对应
# 使用转换器的调试模式
data = GraphModelConverter._prepare_data_for_neomodel(pydantic_obj.model_dump())
print(data)
```

## 示例项目

完整示例请参考 `examples/neomodel_usage.py`

```bash
# 运行示例
python examples/neomodel_usage.py
```

## 相关文档

- [Neomodel官方文档](https://neomodel.readthedocs.io/)
- [Neo4j官方文档](https://neo4j.com/docs/)
- [Pydantic官方文档](https://docs.pydantic.dev/)