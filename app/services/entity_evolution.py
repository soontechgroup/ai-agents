"""
实体演化服务
负责管理实体从简单到复杂的演化过程
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from neomodel import db
from app.models.neomodel.entity import EntityNode
from app.repositories.neomodel import (
    EntityRepository,
    ExtractedKnowledgeRepository
)
from app.core.logger import logger


class EntityEvolutionService:
    """
    实体演化服务
    管理实体在不同抽象层次之间的转换和演化
    
    实体层次：
    1. ExtractedEntity - 自动抽取的简单实体（完全动态）
    2. EntityNode - 类型化的通用实体（半结构化）
    """
    
    def __init__(self):
        self.entity_repo = EntityRepository()
        self.extracted_repo = ExtractedKnowledgeRepository()
    
    async def promote_to_typed(
        self,
        extracted_entity_name: str,
        entity_type: str,
        additional_properties: Optional[Dict] = None
    ) -> Optional[EntityNode]:
        """
        将抽取的实体升级为类型化实体
        
        Args:
            extracted_entity_name: 抽取实体的名称
            entity_type: 目标实体类型
            additional_properties: 额外的属性
        
        Returns:
            升级后的 EntityNode 或 None
        """
        try:
            # 查询抽取的实体
            query = """
            MATCH (e:ExtractedEntity {name: $name})
            RETURN e.name as name, e.type as type, e.description as description,
                   e.source_id as source_id, e.updated_at as updated_at
            """
            results, _ = db.cypher_query(query, {"name": extracted_entity_name})
            
            if not results:
                logger.warning(f"未找到抽取实体: {extracted_entity_name}")
                return None
            
            extracted = results[0]
            
            # 创建或更新 EntityNode
            entity_node = self.entity_repo.find_by_name(extracted_entity_name)
            
            if not entity_node:
                # 创建新的 EntityNode
                entity_data = {
                    "name": extracted[0],
                    "entity_type": entity_type,
                    "description": extracted[2] or "",
                    "digital_human_id": "system",  # 系统级实体
                    "attributes": additional_properties or {}
                }
                
                # 添加源信息
                if extracted[3]:
                    entity_data["attributes"]["source_id"] = extracted[3]
                
                entity_node = self.entity_repo.create(**entity_data)
                logger.info(f"创建类型化实体: {extracted_entity_name} -> {entity_type}")
            else:
                # 更新现有实体
                entity_node.entity_type = entity_type
                if additional_properties:
                    for key, value in additional_properties.items():
                        entity_node.set_attribute(key, value)
                entity_node.update_mention()
                logger.info(f"更新类型化实体: {extracted_entity_name}")
            
            # 建立关联关系
            link_query = """
            MATCH (e:ExtractedEntity {name: $name})
            MATCH (t:EntityNode {uid: $uid})
            MERGE (e)-[:PROMOTED_TO]->(t)
            SET e.promoted_at = datetime()
            """
            db.cypher_query(link_query, {"name": extracted_entity_name, "uid": entity_node.uid})
            
            return entity_node
            
        except Exception as e:
            logger.error(f"升级到类型化实体失败: {str(e)}")
            return None
    
    
    async def merge_duplicates(
        self,
        entity_names: List[str],
        target_name: str
    ) -> bool:
        """
        合并重复的实体
        
        Args:
            entity_names: 要合并的实体名称列表
            target_name: 目标实体名称（保留的实体）
        
        Returns:
            是否成功合并
        """
        try:
            if target_name not in entity_names:
                logger.error(f"目标实体 {target_name} 不在合并列表中")
                return False
            
            # 合并 ExtractedEntity
            merge_extracted_query = """
            MATCH (target:ExtractedEntity {name: $target_name})
            UNWIND $other_names as other_name
            OPTIONAL MATCH (other:ExtractedEntity {name: other_name})
            WHERE other.name <> $target_name
            WITH target, collect(other) as others
            FOREACH (o in others |
                // 转移所有关系到目标实体
                FOREACH (r in [(o)-[rel]-() | rel] |
                    DELETE r
                )
                // 删除重复实体
                DETACH DELETE o
            )
            // 更新目标实体的描述
            SET target.merged_from = $entity_names,
                target.merged_at = datetime()
            RETURN target
            """
            
            other_names = [name for name in entity_names if name != target_name]
            results, _ = db.cypher_query(
                merge_extracted_query,
                {
                    "target_name": target_name,
                    "other_names": other_names,
                    "entity_names": entity_names
                }
            )
            
            # 合并 EntityNode
            target_entity = self.entity_repo.find_by_name(target_name)
            if target_entity:
                for name in other_names:
                    other_entity = self.entity_repo.find_by_name(name)
                    if other_entity:
                        # 使用 EntityNode 的内置合并方法
                        target_entity.merge_with(other_entity)
                        # 添加别名
                        target_entity.add_alias(name)
                        # 删除其他实体
                        other_entity.delete()
            
            logger.info(f"成功合并 {len(entity_names)} 个实体到 {target_name}")
            return True
            
        except Exception as e:
            logger.error(f"合并实体失败: {str(e)}")
            return False
    
    async def enrich_from_extracted(
        self,
        entity_name: str,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        从抽取的数据中丰富现有实体
        
        Args:
            entity_name: 实体名称
            include_relationships: 是否包含关系信息
        
        Returns:
            丰富后的实体信息
        """
        try:
            enriched_data = {
                "name": entity_name,
                "extracted_info": [],
                "relationships": []
            }
            
            # 查询所有相关的抽取信息
            info_query = """
            MATCH (e:ExtractedEntity {name: $name})
            RETURN e.type as type, e.description as description, 
                   e.source_id as source_id, e.updated_at as updated_at
            """
            results, _ = db.cypher_query(info_query, {"name": entity_name})
            
            for row in results:
                enriched_data["extracted_info"].append({
                    "type": row[0],
                    "description": row[1],
                    "source_id": row[2],
                    "updated_at": row[3]
                })
            
            if include_relationships:
                # 查询关系信息
                rel_query = """
                MATCH (e:ExtractedEntity {name: $name})-[r:EXTRACTED_RELATION]-(other)
                RETURN type(r) as rel_type, r.description as description,
                       other.name as other_name, other.type as other_type,
                       startNode(r).name = $name as is_source
                """
                rel_results, _ = db.cypher_query(rel_query, {"name": entity_name})
                
                for row in rel_results:
                    enriched_data["relationships"].append({
                        "type": row[0],
                        "description": row[1],
                        "other_entity": row[2],
                        "other_type": row[3],
                        "direction": "outgoing" if row[4] else "incoming"
                    })
            
            # 不再查询预定义的领域实体
            # 所有实体都是动态的，由 AI 决定其属性
            
            logger.info(f"成功丰富实体: {entity_name}")
            return enriched_data
            
        except Exception as e:
            logger.error(f"丰富实体失败: {str(e)}")
            return {"name": entity_name, "error": str(e)}
    
    async def find_entities(
        self,
        name: Optional[str] = None,
        entity_type: Optional[str] = None,
        include_extracted: bool = True,
        include_typed: bool = True,
        include_domain: bool = True,
        limit: int = 100
    ) -> Dict[str, List[Dict]]:
        """
        统一的实体查询接口
        
        Args:
            name: 实体名称（支持模糊匹配）
            entity_type: 实体类型
            include_extracted: 是否包含抽取的实体
            include_typed: 是否包含类型化实体
            include_domain: 是否包含领域实体
            limit: 返回数量限制
        
        Returns:
            分类的实体列表
        """
        results = {
            "extracted": [],
            "typed": [],
            "domain": []
        }
        
        try:
            # 构建查询条件
            where_conditions = []
            params = {"limit": limit}
            
            if name:
                where_conditions.append("e.name CONTAINS $name")
                params["name"] = name
            
            if entity_type:
                where_conditions.append("e.type = $type OR e.entity_type = $type")
                params["type"] = entity_type
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 查询抽取的实体
            if include_extracted:
                extracted_query = f"""
                MATCH (e:ExtractedEntity)
                {where_clause}
                RETURN e.name as name, e.type as type, e.description as description
                LIMIT $limit
                """
                extracted_results, _ = db.cypher_query(extracted_query, params)
                
                for row in extracted_results:
                    results["extracted"].append({
                        "name": row[0],
                        "type": row[1],
                        "description": row[2],
                        "entity_level": "extracted"
                    })
            
            # 查询类型化实体
            if include_typed:
                typed_entities = self.entity_repo.search(
                    name or "",
                    ["name", "description"] if name else None
                )
                
                for entity in typed_entities[:limit]:
                    if not entity_type or entity.entity_type == entity_type:
                        results["typed"].append({
                            "name": entity.name,
                            "type": entity.entity_type,
                            "description": entity.description,
                            "entity_level": "typed",
                            "attributes": entity.attributes
                        })
            
            # 不再查询预定义的领域实体
            # GraphRAG 理念：让 AI 从数据中发现结构，而不是预设结构
            
            total_count = len(results["extracted"]) + len(results["typed"]) + len(results["domain"])
            logger.info(f"查询实体完成: 找到 {total_count} 个实体")
            
            return results
            
        except Exception as e:
            logger.error(f"查询实体失败: {str(e)}")
            return results
    
    async def get_evolution_path(self, entity_name: str) -> Dict[str, Any]:
        """
        获取实体的演化路径
        
        Args:
            entity_name: 实体名称
        
        Returns:
            实体的演化历史
        """
        try:
            path = {
                "entity_name": entity_name,
                "stages": [],
                "current_level": None
            }
            
            # 检查是否存在抽取实体
            extracted_query = """
            MATCH (e:ExtractedEntity {name: $name})
            RETURN e.updated_at as created_at, e.source_id as source
            """
            extracted_results, _ = db.cypher_query(extracted_query, {"name": entity_name})
            
            if extracted_results:
                path["stages"].append({
                    "level": "extracted",
                    "timestamp": extracted_results[0][0],
                    "source": extracted_results[0][1]
                })
            
            # 检查是否存在类型化实体
            entity_node = self.entity_repo.find_by_name(entity_name)
            if entity_node:
                path["stages"].append({
                    "level": "typed",
                    "timestamp": entity_node.created_at.isoformat() if entity_node.created_at else None,
                    "type": entity_node.entity_type
                })
                path["current_level"] = "typed"
            
            # 不再有预定义的领域实体
            # 最高级别就是 typed entity
            
            return path
            
        except Exception as e:
            logger.error(f"获取演化路径失败: {str(e)}")
            return {"entity_name": entity_name, "error": str(e)}