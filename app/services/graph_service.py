from typing import Dict, List, Any, Optional, Union
import logging
import json

from app.repositories.neomodel import (
    GraphRepository,
    ExtractedKnowledgeRepository
)
from app.models.graph.dynamic_entity import DynamicEntity
from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.entity_evolution import EntityEvolutionService

logger = logging.getLogger(__name__)


class GraphService:
    
    def __init__(self):
        self.graph_repo = GraphRepository()
        self.extracted_knowledge_repo = ExtractedKnowledgeRepository()
        self.knowledge_extractor = KnowledgeExtractor()
        self.entity_evolution = EntityEvolutionService()
    
    async def create_entity(
        self, 
        name: str, 
        types: List[str] = None,
        properties: Dict[str, Any] = None,
        description: str = None,
        source: str = None
    ) -> DynamicEntity:
        try:
            entity = DynamicEntity(
                name=name,
                types=types or [],
                properties=properties or {},
                description=description
            )
            
            if source:
                entity.sources.append(source)
            
            success = self.extracted_knowledge_repo.create_entity(
                name=entity.name,
                entity_type="|".join(entity.types) if entity.types else "unknown",
                description=entity.description or "",
                source_id=entity.uid
            )
            
            if success:
                logger.info(f"创建动态实体成功: {name} (类型: {entity.types})")
                return entity
            else:
                logger.error(f"创建动态实体失败: {name}")
                return None
                
        except Exception as e:
            logger.error(f"创建实体异常: {str(e)}")
            raise
    
    async def update_entity(
        self,
        name: str,
        add_types: List[str] = None,
        add_properties: Dict[str, Any] = None,
        new_context: Dict[str, Any] = None,
        source: str = None
    ) -> bool:
        try:
            entities = self.extracted_knowledge_repo.find_entities_by_names([name])
            
            if not entities:
                logger.warning(f"未找到实体: {name}")
                return False
            
            logger.info(f"更新实体: {name}")
            return True
            
        except Exception as e:
            logger.error(f"更新实体失败: {str(e)}")
            return False
    
    async def find_entities(
        self,
        query: str = None,
        entity_types: List[str] = None,
        limit: int = 100
    ) -> List[DynamicEntity]:
        try:
            results = await self.entity_evolution.find_entities(
                name=query,
                entity_type=entity_types[0] if entity_types else None,
                include_extracted=True,
                include_typed=True,
                include_domain=False
            )
            
            entities = []
            for category in ['extracted', 'typed']:
                for item in results.get(category, [])[:limit]:
                    entity = DynamicEntity(
                        name=item['name'],
                        types=[item.get('type', 'unknown')],
                        description=item.get('description'),
                        properties=item.get('attributes', {})
                    )
                    entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"查找实体失败: {str(e)}")
            return []
    
    async def create_relationship(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        try:
            description = properties.get('description', '') if properties else ''
            
            success = self.extracted_knowledge_repo.create_relationship(
                source=source_name,
                target=target_name,
                description=f"{relationship_type}: {description}"
            )
            
            if success:
                logger.info(f"创建关系成功: {source_name} -[{relationship_type}]-> {target_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"创建关系失败: {str(e)}")
            return False
    
    async def extract_and_store_knowledge(
        self,
        text: str,
        source_id: Optional[str] = None
    ) -> Dict:
        try:
            extraction_result = await self.knowledge_extractor.extract(text)
            
            for entity_data in extraction_result['entities']:
                await self.create_entity(
                    name=entity_data['name'],
                    types=[entity_data['type']],
                    description=entity_data.get('description'),
                    source=source_id
                )
            
            for rel_data in extraction_result['relationships']:
                await self.create_relationship(
                    source_name=rel_data['source'],
                    target_name=rel_data['target'],
                    relationship_type=rel_data.get('relation_type', 'RELATED'),
                    properties={'description': rel_data.get('description')}
                )
            
            logger.info(
                f"知识抽取完成: {len(extraction_result['entities'])} 个实体, "
                f"{len(extraction_result['relationships'])} 个关系"
            )
            
            return {
                "success": True,
                "entities_count": len(extraction_result['entities']),
                "relationships_count": len(extraction_result['relationships']),
                "entities": extraction_result['entities'],
                "relationships": extraction_result['relationships']
            }
            
        except Exception as e:
            logger.error(f"知识抽取失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_relevant_context(self, query: str) -> str:
        try:
            extraction = await self.knowledge_extractor.extract(query)
            
            entity_names = [e['name'] for e in extraction['entities']]
            found_entities = self.extracted_knowledge_repo.find_entities_by_names(entity_names)
            
            context_parts = []
            for entity in found_entities:
                context_parts.append(
                    f"相关实体: {entity['name']} ({entity['type']}): {entity['description']}"
                )
                
                entity_context = self.extracted_knowledge_repo.get_entity_context(entity['name'])
                if entity_context:
                    context_parts.append(
                        f"  - 相关连接: {entity_context.get('relationships', 0)} 个关系, "
                        f"{entity_context.get('related_entities', 0)} 个相关实体"
                    )
            
            return "\n".join(context_parts) if context_parts else "暂无相关上下文信息"
            
        except Exception as e:
            logger.error(f"获取上下文失败: {str(e)}")
            return ""
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        return self.graph_repo.get_statistics()
    
    async def find_shortest_path(self, from_name: str, to_name: str) -> Optional[Dict[str, Any]]:
        return self.graph_repo.find_shortest_path(from_name, to_name)
    
    async def list_relationships(
        self,
        relationship_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        return self.graph_repo.list_all_relationships(relationship_type, limit)
    
    async def evolve_entity_to_typed(
        self,
        entity_name: str,
        entity_type: str,
        additional_properties: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        try:
            result = await self.entity_evolution.promote_to_typed(
                entity_name,
                entity_type,
                additional_properties
            )
            
            if result:
                return {
                    "success": True,
                    "entity": result.to_dict(),
                    "message": f"实体 {entity_name} 已升级为类型化实体"
                }
            else:
                return {
                    "success": False,
                    "error": "升级失败"
                }
                
        except Exception as e:
            logger.error(f"实体演化失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def merge_entities(
        self,
        entity_names: List[str],
        target_name: str
    ) -> Dict[str, Any]:
        try:
            success = await self.entity_evolution.merge_duplicates(entity_names, target_name)
            
            if success:
                enriched = await self.entity_evolution.enrich_from_extracted(target_name)
                
                return {
                    "success": True,
                    "merged_entity": target_name,
                    "merged_count": len(entity_names),
                    "entity_info": enriched
                }
            else:
                return {
                    "success": False,
                    "error": "合并失败"
                }
                
        except Exception as e:
            logger.error(f"合并实体失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_entity_evolution_path(self, entity_name: str) -> Dict[str, Any]:
        try:
            path = await self.entity_evolution.get_evolution_path(entity_name)
            
            if path.get('current_level') == 'extracted':
                path['next_step'] = {
                    "level": "typed",
                    "action": "promote_to_typed",
                    "description": "可以升级为类型化实体以获得更好的管理"
                }
            else:
                path['next_step'] = None
            
            return path
            
        except Exception as e:
            logger.error(f"获取演化路径失败: {str(e)}")
            return {"entity_name": entity_name, "error": str(e)}
    
    async def store_digital_human_entity(
        self,
        digital_human_id: int,
        entity: Dict[str, Any]
    ) -> bool:
        """存储数字人的知识实体到图数据库"""
        try:
            import json
            query = """
            MERGE (dh:DigitalHuman {id: $dh_id})
            MERGE (k:Knowledge {
                name: $name,
                digital_human_id: $dh_id
            })
            SET k.type = $type,
                k.types = $types,
                k.confidence = $confidence,
                k.properties = $properties,
                k.updated_at = datetime()
            MERGE (dh)-[r:HAS_KNOWLEDGE]->(k)
            SET r.updated_at = datetime()
            """
            
            self.graph_repo.execute_cypher(query, {
                "dh_id": digital_human_id,
                "name": entity.get("name"),
                "type": entity.get("type", "unknown"),
                "types": json.dumps(entity.get("types", [])),
                "confidence": entity.get("confidence", 0.5),
                "properties": json.dumps(entity.get("properties", {}))
            })
            
            logger.info(f"存储数字人实体成功: {entity.get('name')} (数字人ID: {digital_human_id})")
            return True
            
        except Exception as e:
            logger.error(f"存储数字人实体失败: {str(e)}")
            return False
    
    async def store_digital_human_relationship(
        self,
        digital_human_id: int,
        relationship: Dict[str, Any]
    ) -> bool:
        """存储数字人的知识关系到图数据库"""
        try:
            import json
            query = """
            MATCH (k1:Knowledge {
                name: $source,
                digital_human_id: $dh_id
            })
            MATCH (k2:Knowledge {
                name: $target,
                digital_human_id: $dh_id
            })
            MERGE (k1)-[r:RELATES_TO]->(k2)
            SET r.relation_type = $relation_type,
                r.confidence = $confidence,
                r.properties = $properties,
                r.updated_at = datetime()
            """
            
            self.graph_repo.execute_cypher(query, {
                "dh_id": digital_human_id,
                "source": relationship.get("source"),
                "target": relationship.get("target"),
                "relation_type": relationship.get("relation_type"),
                "confidence": relationship.get("confidence", 0.5),
                "properties": json.dumps(relationship.get("properties", {}))
            })
            
            logger.info(f"存储数字人关系成功: {relationship.get('source')} -> {relationship.get('target')}")
            return True
            
        except Exception as e:
            logger.error(f"存储数字人关系失败: {str(e)}")
            return False
    
    def get_digital_human_knowledge_context(self, digital_human_id: int) -> Dict[str, Any]:
        """获取数字人的知识上下文（同步方法）"""
        try:
            query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            RETURN k.name as name, k.type as type, k.properties as properties
            ORDER BY k.updated_at DESC
            LIMIT 100
            """
            
            results, _ = self.graph_repo.execute_cypher(query, {"dh_id": digital_human_id})
            
            context = {
                "total_knowledge_points": 0,
                "categories": {},
                "recent_entities": []
            }
            
            for row in results:
                context["total_knowledge_points"] += 1
                
                entity_type = row.get("type", "unknown")
                if entity_type not in context["categories"]:
                    context["categories"][entity_type] = {
                        "count": 0,
                        "examples": []
                    }
                
                context["categories"][entity_type]["count"] += 1
                if len(context["categories"][entity_type]["examples"]) < 3:
                    context["categories"][entity_type]["examples"].append(row.get("name"))
                
                if len(context["recent_entities"]) < 10:
                    context["recent_entities"].append({
                        "name": row.get("name"),
                        "type": entity_type
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"获取数字人知识上下文失败: {str(e)}")
            return {
                "total_knowledge_points": 0,
                "categories": {},
                "recent_entities": []
            }
    
    async def get_digital_human_memory_graph(
        self,
        digital_human_id: int,
        limit: int = 100,
        node_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取数字人的记忆图谱数据，用于前端可视化展示
        
        Args:
            digital_human_id: 数字人ID
            limit: 返回的最大节点数
            node_types: 要筛选的节点类型列表
            
        Returns:
            包含节点、边和统计信息的字典，适合前端图形化展示
        """
        try:
            # 查询知识节点
            node_query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            WHERE $types IS NULL OR k.type IN $types
            RETURN k.name as id,
                   k.name as label,
                   k.type as type,
                   k.confidence as confidence,
                   k.properties as properties,
                   k.updated_at as updated_at
            ORDER BY k.updated_at DESC
            LIMIT $limit
            """
            
            node_results, _ = self.graph_repo.execute_cypher(node_query, {
                "dh_id": digital_human_id,
                "types": node_types,
                "limit": limit
            })
            
            # 构建节点列表和节点名称集合
            nodes = []
            node_names = set()
            type_counts = {}
            
            for row in node_results:
                # row 是一个列表，按照查询中的顺序访问
                # [id, label, type, confidence, properties, updated_at]
                node_id = row[0] if len(row) > 0 else None
                node_label = row[1] if len(row) > 1 else ""
                node_type = row[2] if len(row) > 2 else "unknown"
                confidence = row[3] if len(row) > 3 else 0.5
                properties = row[4] if len(row) > 4 else "{}"
                updated_at = row[5] if len(row) > 5 else None
                
                # 统计各类型节点数量
                if node_type not in type_counts:
                    type_counts[node_type] = 0
                type_counts[node_type] += 1
                
                # 根据confidence计算节点大小
                size = 10 + confidence * 20  # 基础大小10，最大30
                
                nodes.append({
                    "id": node_id,
                    "label": node_label,
                    "type": node_type,
                    "size": size,
                    "confidence": confidence,
                    "properties": json.loads(properties) if isinstance(properties, str) else properties or {},
                    "updated_at": str(updated_at) if updated_at else None
                })
                node_names.add(node_id)
            
            # 查询关系（只查询已有节点之间的关系）
            edges = []
            if node_names:
                rel_query = """
                MATCH (k1:Knowledge {digital_human_id: $dh_id})-[r:RELATES_TO]->(k2:Knowledge {digital_human_id: $dh_id})
                WHERE k1.name IN $node_names AND k2.name IN $node_names
                RETURN k1.name as source,
                       k2.name as target,
                       r.relation_type as type,
                       r.confidence as confidence,
                       r.properties as properties
                LIMIT $limit
                """
                
                rel_results, _ = self.graph_repo.execute_cypher(rel_query, {
                    "dh_id": digital_human_id,
                    "node_names": list(node_names),
                    "limit": limit
                })
                
                for row in rel_results:
                    # row 是一个列表，按照查询中的顺序访问
                    # [source, target, type, confidence, properties]
                    source = row[0] if len(row) > 0 else None
                    target = row[1] if len(row) > 1 else None
                    rel_type = row[2] if len(row) > 2 else "RELATES_TO"
                    rel_confidence = row[3] if len(row) > 3 else 0.5
                    rel_properties = row[4] if len(row) > 4 else "{}"
                    
                    edges.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                        "confidence": rel_confidence,
                        "properties": json.loads(rel_properties) if isinstance(rel_properties, str) else rel_properties or {}
                    })
            
            # 获取总体统计信息
            stats_query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            RETURN count(k) as total_nodes
            """
            stats_results, _ = self.graph_repo.execute_cypher(stats_query, {"dh_id": digital_human_id})
            total_nodes = stats_results[0][0] if stats_results and len(stats_results) > 0 else 0
            
            rel_stats_query = """
            MATCH (k1:Knowledge {digital_human_id: $dh_id})-[r:RELATES_TO]->(k2:Knowledge {digital_human_id: $dh_id})
            RETURN count(r) as total_edges
            """
            rel_stats_results, _ = self.graph_repo.execute_cypher(rel_stats_query, {"dh_id": digital_human_id})
            total_edges = rel_stats_results[0][0] if rel_stats_results and len(rel_stats_results) > 0 else 0
            
            return {
                "nodes": nodes,
                "edges": edges,
                "statistics": {
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "displayed_nodes": len(nodes),
                    "displayed_edges": len(edges),
                    "categories": type_counts
                }
            }
            
        except Exception as e:
            logger.error(f"获取数字人记忆图谱失败: {str(e)}")
            return {
                "nodes": [],
                "edges": [],
                "statistics": {
                    "total_nodes": 0,
                    "total_edges": 0,
                    "displayed_nodes": 0,
                    "displayed_edges": 0,
                    "categories": {}
                },
                "error": str(e)
            }
    
    async def search_digital_human_memories(
        self,
        digital_human_id: int,
        query: str,
        node_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """搜索数字人的记忆节点"""
        try:
            type_filter = ""
            if node_types:
                type_filter = f"AND k.type IN {node_types}"
            
            search_query = f"""
            MATCH (dh:DigitalHuman {{id: $dh_id}})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            WHERE toLower(k.name) CONTAINS toLower($query) 
                  OR toLower(k.properties) CONTAINS toLower($query)
                  {type_filter}
            RETURN k.name as id,
                   k.name as label,
                   k.type as type,
                   k.confidence as confidence,
                   k.properties as properties,
                   k.updated_at as updated_at
            ORDER BY k.confidence DESC, k.updated_at DESC
            LIMIT $limit
            """
            
            results, _ = self.graph_repo.execute_cypher(search_query, {
                "dh_id": digital_human_id,
                "query": query,
                "limit": limit
            })
            
            nodes = []
            for row in results:
                node_id = row[0] if len(row) > 0 else None
                node_label = row[1] if len(row) > 1 else ""
                node_type = row[2] if len(row) > 2 else "unknown"
                confidence = row[3] if len(row) > 3 else 0.5
                properties = row[4] if len(row) > 4 else "{}"
                updated_at = row[5] if len(row) > 5 else None
                
                parsed_props = json.loads(properties) if isinstance(properties, str) else properties or {}
                
                nodes.append({
                    "id": node_id,
                    "label": node_label,
                    "type": node_type,
                    "confidence": confidence,
                    "properties": parsed_props,
                    "updated_at": str(updated_at) if updated_at else None
                })
            
            return {
                "query": query,
                "results": nodes,
                "count": len(nodes),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"搜索数字人记忆失败: {str(e)}")
            return {
                "query": query,
                "results": [],
                "count": 0,
                "success": False,
                "error": str(e)
            }
    
    async def get_memory_node_detail(
        self,
        digital_human_id: int,
        node_id: str,
        include_relations: bool = True,
        relation_depth: int = 1
    ) -> Dict[str, Any]:
        """获取记忆节点的详细信息"""
        try:
            node_query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge {name: $node_id})
            RETURN k.name as id,
                   k.name as label,
                   k.type as type,
                   k.confidence as confidence,
                   k.properties as properties,
                   k.types as types,
                   k.updated_at as updated_at
            """
            
            node_results, _ = self.graph_repo.execute_cypher(node_query, {
                "dh_id": digital_human_id,
                "node_id": node_id
            })
            
            if not node_results:
                return {"error": "Node not found", "success": False}
            
            row = node_results[0]
            node_detail = {
                "id": row[0] if len(row) > 0 else None,
                "label": row[1] if len(row) > 1 else "",
                "type": row[2] if len(row) > 2 else "unknown",
                "confidence": row[3] if len(row) > 3 else 0.5,
                "properties": json.loads(row[4]) if isinstance(row[4], str) else row[4] or {},
                "types": json.loads(row[5]) if isinstance(row[5], str) else row[5] or [],
                "updated_at": str(row[6]) if len(row) > 6 and row[6] else None
            }
            
            relations = []
            connected_nodes = []
            
            if include_relations:
                rel_query = f"""
                MATCH (k1:Knowledge {{name: $node_id, digital_human_id: $dh_id}})
                MATCH (k1)-[r:RELATES_TO*1..{relation_depth}]-(k2:Knowledge {{digital_human_id: $dh_id}})
                RETURN DISTINCT 
                       type(r[0]) as rel_type,
                       k1.name as source,
                       k2.name as target,
                       k2.type as target_type,
                       k2.properties as target_props,
                       r[0].confidence as rel_confidence,
                       r[0].properties as rel_props
                LIMIT 100
                """
                
                rel_results, _ = self.graph_repo.execute_cypher(rel_query, {
                    "dh_id": digital_human_id,
                    "node_id": node_id
                })
                
                seen_nodes = set()
                for row in rel_results:
                    rel_type = row[0] if len(row) > 0 else "RELATES_TO"
                    source = row[1] if len(row) > 1 else None
                    target = row[2] if len(row) > 2 else None
                    target_type = row[3] if len(row) > 3 else "unknown"
                    target_props = json.loads(row[4]) if isinstance(row[4], str) else row[4] or {}
                    rel_confidence = row[5] if len(row) > 5 else 0.5
                    rel_props = json.loads(row[6]) if isinstance(row[6], str) else row[6] or {}
                    
                    relations.append({
                        "type": rel_type,
                        "source": source,
                        "target": target,
                        "confidence": rel_confidence,
                        "properties": rel_props
                    })
                    
                    if target not in seen_nodes:
                        connected_nodes.append({
                            "id": target,
                            "label": target,
                            "type": target_type,
                            "properties": target_props
                        })
                        seen_nodes.add(target)
            
            return {
                "node": node_detail,
                "relations": relations,
                "connected_nodes": connected_nodes,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"获取记忆节点详情失败: {str(e)}")
            return {
                "error": str(e),
                "success": False
            }
    
    async def get_memory_statistics(
        self,
        digital_human_id: int,
        include_timeline: bool = False
    ) -> Dict[str, Any]:
        """获取数字人的记忆统计信息"""
        try:
            node_stats_query = """
            MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
            RETURN k.type as type, count(k) as count
            ORDER BY count DESC
            """
            
            node_results, _ = self.graph_repo.execute_cypher(node_stats_query, {
                "dh_id": digital_human_id
            })
            
            node_categories = {}
            total_nodes = 0
            for row in node_results:
                node_type = row[0] if len(row) > 0 else "unknown"
                count = row[1] if len(row) > 1 else 0
                node_categories[node_type] = count
                total_nodes += count
            
            edge_stats_query = """
            MATCH (k1:Knowledge {digital_human_id: $dh_id})-[r:RELATES_TO]->(k2:Knowledge {digital_human_id: $dh_id})
            RETURN r.relation_type as type, count(r) as count
            ORDER BY count DESC
            """
            
            edge_results, _ = self.graph_repo.execute_cypher(edge_stats_query, {
                "dh_id": digital_human_id
            })
            
            edge_types = {}
            total_edges = 0
            for row in edge_results:
                edge_type = row[0] if len(row) > 0 else "RELATES_TO"
                count = row[1] if len(row) > 1 else 0
                edge_types[edge_type] = count
                total_edges += count
            
            network_density = 0
            avg_connections = 0
            if total_nodes > 1:
                max_possible_edges = total_nodes * (total_nodes - 1) / 2
                network_density = total_edges / max_possible_edges if max_possible_edges > 0 else 0
                avg_connections = (total_edges * 2) / total_nodes if total_nodes > 0 else 0
            
            result = {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_categories": node_categories,
                "edge_types": edge_types,
                "network_density": round(network_density, 4),
                "avg_connections_per_node": round(avg_connections, 2)
            }
            
            if include_timeline:
                timeline_query = """
                MATCH (dh:DigitalHuman {id: $dh_id})-[:HAS_KNOWLEDGE]->(k:Knowledge)
                WHERE k.updated_at IS NOT NULL
                RETURN date(k.updated_at) as date, count(k) as count
                ORDER BY date DESC
                LIMIT 30
                """
                
                timeline_results, _ = self.graph_repo.execute_cypher(timeline_query, {
                    "dh_id": digital_human_id
                })
                
                timeline = []
                for row in timeline_results:
                    date = str(row[0]) if len(row) > 0 else None
                    count = row[1] if len(row) > 1 else 0
                    if date:
                        timeline.append({"date": date, "count": count})
                
                result["timeline"] = timeline
            
            return result
            
        except Exception as e:
            logger.error(f"获取记忆统计失败: {str(e)}")
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "node_categories": {},
                "edge_types": {},
                "network_density": 0,
                "avg_connections_per_node": 0,
                "error": str(e)
            }