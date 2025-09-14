from typing import List, Dict, Any, Optional
from app.services.embedding_service import EmbeddingService
from app.repositories.neomodel.extracted_knowledge import ExtractedKnowledgeRepository
from app.repositories.neomodel.graph_repository import GraphRepository
from app.core.logger import logger
from neomodel import db


class HybridSearchService:
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.extracted_knowledge_repo = ExtractedKnowledgeRepository()
        self.graph_repo = GraphRepository()
    
    async def search(
        self,
        query: str,
        digital_human_id: int,
        mode: str = "hybrid",
        entity_limit: int = 20,
        relationship_limit: int = 10,
        expand_graph: bool = True
    ) -> Dict[str, Any]:
        """
        搜索模式：
        - semantic: 仅语义搜索
        - graph: 仅图搜索
        - hybrid: 混合搜索（默认）
        """
        
        results = {
            "entities": [],
            "relationships": [],
            "source_texts": [],
            "mode": mode,
            "query": query
        }
        
        try:
            if mode in ["semantic", "hybrid"]:
                # 语义搜索实体
                semantic_entities = await self.embedding_service.semantic_search(
                    query=query,
                    collection="entity_embeddings",
                    digital_human_id=digital_human_id,
                    k=entity_limit
                )
                
                # 处理语义搜索结果
                for entity in semantic_entities:
                    entity_data = {
                        "name": entity["metadata"].get("entity_name", ""),
                        "types": entity["metadata"].get("entity_types", "[]"),
                        "description": entity["metadata"].get("description", ""),
                        "confidence": float(entity["metadata"].get("confidence", 0.5)),
                        "distance": entity["distance"],
                        "source": "semantic_search"
                    }
                    results["entities"].append(entity_data)
                
                # 语义搜索关系
                semantic_relations = await self.embedding_service.semantic_search(
                    query=query,
                    collection="relationship_embeddings",
                    digital_human_id=digital_human_id,
                    k=relationship_limit
                )
                
                for rel in semantic_relations:
                    rel_data = {
                        "source": rel["metadata"].get("source", ""),
                        "target": rel["metadata"].get("target", ""),
                        "types": rel["metadata"].get("relation_types", "[]"),
                        "description": rel["metadata"].get("description", ""),
                        "confidence": float(rel["metadata"].get("confidence", 0.5)),
                        "strength": float(rel["metadata"].get("strength", 0.5)),
                        "distance": rel["distance"],
                        "source": "semantic_search"
                    }
                    results["relationships"].append(rel_data)
                
                logger.info(f"Semantic search found {len(semantic_entities)} entities and {len(semantic_relations)} relationships")
            
            if mode in ["graph", "hybrid"] and expand_graph and results["entities"]:
                # 基于找到的实体进行图扩展
                entity_names = [e["name"] for e in results["entities"][:5]]  # 只取前5个实体
                
                for entity_name in entity_names:
                    graph_neighbors = await self._get_graph_neighbors(entity_name, digital_human_id)
                    
                    # 添加邻居实体
                    for neighbor in graph_neighbors.get("entities", []):
                        # 检查是否已存在
                        if not any(e["name"] == neighbor["name"] for e in results["entities"]):
                            neighbor["source"] = "graph_expansion"
                            results["entities"].append(neighbor)
                    
                    # 添加关系
                    for relation in graph_neighbors.get("relationships", []):
                        # 检查是否已存在
                        exists = any(
                            r["source"] == relation["source"] and 
                            r["target"] == relation["target"] 
                            for r in results["relationships"]
                        )
                        if not exists:
                            relation["source_type"] = "graph_expansion"
                            results["relationships"].append(relation)
                
                logger.info(f"Graph expansion added entities and relationships")
            
            # 去重和排序
            results = self._deduplicate_and_rank(results)
            
            # 添加统计信息
            results["statistics"] = {
                "total_entities": len(results["entities"]),
                "total_relationships": len(results["relationships"]),
                "semantic_entities": len([e for e in results["entities"] if e.get("source") == "semantic_search"]),
                "graph_entities": len([e for e in results["entities"] if e.get("source") == "graph_expansion"])
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise
    
    async def _get_graph_neighbors(self, entity_name: str, digital_human_id: int, depth: int = 1) -> Dict[str, Any]:
        """获取实体的图邻居"""
        try:
            query = """
            MATCH (dh:DigitalHuman {id: $digital_human_id})
            MATCH (dh)-[:HAS_KNOWLEDGE]->(e:ExtractedEntity {name: $name})
            OPTIONAL MATCH (e)-[r]-(neighbor:ExtractedEntity)<-[:HAS_KNOWLEDGE]-(dh)
            RETURN e, r, neighbor
            LIMIT 20
            """
            
            results, _ = db.cypher_query(query, {"name": entity_name, "digital_human_id": digital_human_id})
            
            entities = []
            relationships = []
            
            for row in results:
                # 解析邻居实体
                if row[2]:  # neighbor exists
                    neighbor_node = row[2]
                    entities.append({
                        "name": neighbor_node.get("name", ""),
                        "types": [neighbor_node.get("type", "unknown")],
                        "description": neighbor_node.get("description", ""),
                        "confidence": 0.7  # 图扩展的置信度设置为0.7
                    })
                
                # 解析关系
                if row[1]:  # relationship exists
                    rel = row[1]
                    relationships.append({
                        "source": entity_name,
                        "target": row[2].get("name", "") if row[2] else "",
                        "types": ["EXTRACTED_RELATION"],
                        "description": rel.get("description", ""),
                        "confidence": 0.7,
                        "strength": 0.5
                    })
            
            return {
                "entities": entities,
                "relationships": relationships
            }
            
        except Exception as e:
            logger.error(f"Failed to get graph neighbors for {entity_name}: {str(e)}")
            return {"entities": [], "relationships": []}
    
    def _deduplicate_and_rank(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """去重并排序结果"""
        
        # 实体去重（基于名称）
        seen_entities = {}
        for entity in results["entities"]:
            name = entity["name"]
            if name not in seen_entities:
                seen_entities[name] = entity
            else:
                # 如果已存在，选择置信度更高的
                if entity.get("confidence", 0) > seen_entities[name].get("confidence", 0):
                    seen_entities[name] = entity
        
        # 关系去重（基于源和目标）
        seen_relations = {}
        for rel in results["relationships"]:
            key = f"{rel['source']}->{rel['target']}"
            if key not in seen_relations:
                seen_relations[key] = rel
            else:
                # 如果已存在，选择置信度更高的
                if rel.get("confidence", 0) > seen_relations[key].get("confidence", 0):
                    seen_relations[key] = rel
        
        # 排序（语义搜索的结果优先，然后按置信度）
        entities_list = list(seen_entities.values())
        entities_list.sort(
            key=lambda x: (
                x.get("source") != "semantic_search",  # 语义搜索结果优先
                -x.get("confidence", 0),  # 置信度降序
                x.get("distance", 1)  # 距离升序
            )
        )
        
        relations_list = list(seen_relations.values())
        relations_list.sort(
            key=lambda x: (
                x.get("source") != "semantic_search",
                -x.get("confidence", 0),
                x.get("distance", 1)
            )
        )
        
        results["entities"] = entities_list
        results["relationships"] = relations_list
        
        return results
    
    async def search_entities(self, query: str, digital_human_id: int, k: int = 10) -> List[Dict[str, Any]]:
        """仅搜索实体"""
        return await self.embedding_service.semantic_search(
            query=query,
            collection="entity_embeddings",
            digital_human_id=digital_human_id,
            k=k
        )
    
    async def search_relationships(self, query: str, digital_human_id: int, k: int = 10) -> List[Dict[str, Any]]:
        """仅搜索关系"""
        return await self.embedding_service.semantic_search(
            query=query,
            collection="relationship_embeddings",
            digital_human_id=digital_human_id,
            k=k
        )
    
    async def search_text_chunks(self, query: str, digital_human_id: int, k: int = 10) -> List[Dict[str, Any]]:
        """搜索文本块"""
        return await self.embedding_service.semantic_search(
            query=query,
            collection="text_chunk_embeddings",
            digital_human_id=digital_human_id,
            k=k
        )