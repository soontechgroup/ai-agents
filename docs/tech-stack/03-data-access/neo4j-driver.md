# Neo4j Python 驱动

## 📚 使用说明

项目使用 Neomodel ORM 访问 Neo4j，但有时需要直接使用 cypher_query 执行复杂查询。

## 🛠 框架配置

### 通过 Neomodel 使用
```python
# 项目主要使用 Neomodel ORM
from neomodel import db

# 执行原生 Cypher 查询
results, meta = db.cypher_query(
    "MATCH (e:ExtractedEntity) RETURN e.name LIMIT 5"
)
```

### 直接查询示例
```python
# 复杂的图查询（无法通过 ORM 简单实现时）
from neomodel import db

def get_entity_neighbors(entity_name: str, digital_human_id: int):
    query = """
    MATCH (dh:DigitalHuman {id: $digital_human_id})
    MATCH (dh)-[:HAS_KNOWLEDGE]->(e:ExtractedEntity {name: $name})
    OPTIONAL MATCH (e)-[r]-(neighbor:ExtractedEntity)<-[:HAS_KNOWLEDGE]-(dh)
    RETURN e, r, neighbor
    LIMIT 20
    """

    results, meta = db.cypher_query(query, {
        "name": entity_name,
        "digital_human_id": digital_human_id
    })

    return results

# 批量操作
def batch_create_relationships(relationships_data: list):
    query = """
    UNWIND $relationships as rel
    MATCH (a:ExtractedEntity {id: rel.from_id})
    MATCH (b:ExtractedEntity {id: rel.to_id})
    CREATE (a)-[:RELATES_TO {strength: rel.strength}]->(b)
    """

    db.cypher_query(query, {"relationships": relationships_data})
```

Neo4j Driver 主要通过 Neomodel 的 `cypher_query` 方法使用，用于执行复杂的图查询操作。