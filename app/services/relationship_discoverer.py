from typing import Dict, List, Set, Tuple, Optional
import logging
from collections import defaultdict
from datetime import datetime

from app.models.graph.dynamic_entity import DynamicEntity
from app.models.graph.dynamic_relationship import DynamicRelationship
from app.services.extraction_config import ExtractionConfig

logger = logging.getLogger(__name__)


class CrossChunkRelationshipDiscoverer:
    """跨块关系发现器"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        
        # 关系推理规则
        self.inference_rules = {
            # 传递关系：如果A works_for B，B part_of C，则A间接关联C
            ("WORKS_FOR", "PART_OF"): ("INDIRECTLY_WORKS_FOR", 0.6),
            ("LOCATED_IN", "PART_OF"): ("INDIRECTLY_LOCATED_IN", 0.5),
            
            # 对称关系
            "COLLABORATES_WITH": ("COLLABORATES_WITH", 1.0),  # 双向
            "COMPETES_WITH": ("COMPETES_WITH", 1.0),  # 双向
        }
        
        # 关系强度衰减
        self.distance_decay = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2}
    
    def discover_relationships(self, 
                             chunks_results: List[Dict], 
                             merged_entities: Dict[str, DynamicEntity]) -> List[DynamicRelationship]:
        """
        发现跨块关系
        
        Args:
            chunks_results: 每个块的抽取结果
            merged_entities: 已合并的实体映射
            
        Returns:
            发现的跨块关系列表
        """
        if not self.config.enable_cross_chunk_relations:
            return []
        
        cross_chunk_relations = []
        
        # 1. 分析实体共现模式
        cooccurrence_relations = self._analyze_entity_cooccurrence(chunks_results, merged_entities)
        cross_chunk_relations.extend(cooccurrence_relations)
        
        # 2. 推理传递关系
        if len(chunks_results) > 1:
            transitive_relations = self._infer_transitive_relationships(chunks_results, merged_entities)
            cross_chunk_relations.extend(transitive_relations)
        
        # 3. 验证和过滤关系
        validated_relations = self._validate_relationships(cross_chunk_relations, merged_entities)
        
        if self.config.enable_debug_logging:
            logger.debug(f"发现跨块关系: {len(validated_relations)} 个")
        
        return validated_relations
    
    def _analyze_entity_cooccurrence(self, 
                                   chunks_results: List[Dict], 
                                   merged_entities: Dict[str, DynamicEntity]) -> List[DynamicRelationship]:
        """分析实体共现模式"""
        
        entity_chunks = defaultdict(list)  # entity_name -> [chunk_indices]
        
        # 收集每个实体出现的块索引
        for chunk_idx, chunk_result in enumerate(chunks_results):
            for entity_data in chunk_result.get('entities', []):
                entity_name = entity_data.get('name', '').strip()
                if entity_name and entity_name in merged_entities:
                    entity_chunks[entity_name].append(chunk_idx)
        
        # 查找共现实体对
        cooccurrence_relations = []
        entity_names = list(entity_chunks.keys())
        
        for i, entity1_name in enumerate(entity_names):
            for entity2_name in entity_names[i+1:]:
                # 检查两个实体是否在同一块中出现
                common_chunks = set(entity_chunks[entity1_name]) & set(entity_chunks[entity2_name])
                
                if common_chunks:
                    relation = self._create_cooccurrence_relationship(
                        entity1_name, entity2_name, common_chunks, merged_entities
                    )
                    if relation:
                        cooccurrence_relations.append(relation)
        
        return cooccurrence_relations
    
    def _create_cooccurrence_relationship(self, 
                                        entity1_name: str, 
                                        entity2_name: str, 
                                        common_chunks: Set[int],
                                        merged_entities: Dict[str, DynamicEntity]) -> Optional[DynamicRelationship]:
        """基于共现创建关系"""
        
        entity1 = merged_entities[entity1_name]
        entity2 = merged_entities[entity2_name]
        
        # 基于实体类型推断关系类型
        relation_type = self._infer_relation_type_from_entities(entity1, entity2)
        
        if not relation_type:
            return None
        
        # 计算关系强度（基于共现频率）
        strength = min(1.0, len(common_chunks) * 0.3 + 0.4)
        confidence = min(1.0, len(common_chunks) * 0.2 + 0.5)
        
        relationship = DynamicRelationship(
            source_name=entity1_name,
            target_name=entity2_name,
            relationship_types=[relation_type],
            properties={
                "discovery_method": "cooccurrence",
                "common_chunks": list(common_chunks),
                "cooccurrence_frequency": len(common_chunks)
            },
            confidence=confidence,
            strength=strength
        )
        
        return relationship
    
    def _infer_relation_type_from_entities(self, entity1: DynamicEntity, entity2: DynamicEntity) -> Optional[str]:
        """基于实体类型推断关系类型"""
        
        types1 = set(t.lower() for t in entity1.types)
        types2 = set(t.lower() for t in entity2.types)
        
        # 人-组织关系
        if ("person" in types1 or "ceo" in types1) and ("organization" in types2 or "company" in types2):
            return "ASSOCIATED_WITH"
        if ("person" in types2 or "ceo" in types2) and ("organization" in types1 or "company" in types1):
            return "ASSOCIATED_WITH"
        
        # 组织-地点关系
        if ("organization" in types1 or "company" in types1) and ("location" in types2):
            return "POTENTIALLY_LOCATED_IN"
        if ("organization" in types2 or "company" in types2) and ("location" in types1):
            return "POTENTIALLY_LOCATED_IN"
        
        # 产品-组织关系
        if ("product" in types1) and ("organization" in types2 or "company" in types2):
            return "POTENTIALLY_CREATED_BY"
        if ("product" in types2) and ("organization" in types1 or "company" in types1):
            return "POTENTIALLY_CREATED_BY"
        
        # 同类实体关系
        if types1 & types2:
            if "organization" in types1 or "company" in types1:
                return "RELATED_ORGANIZATION"
            elif "person" in types1:
                return "ASSOCIATED_PERSON"
        
        return None
    
    def _infer_transitive_relationships(self, 
                                      chunks_results: List[Dict], 
                                      merged_entities: Dict[str, DynamicEntity]) -> List[DynamicRelationship]:
        """推理传递关系"""
        
        # 收集所有已知关系
        all_relations = {}  # (source, target) -> relation_data
        
        for chunk_result in chunks_results:
            for rel_data in chunk_result.get('relationships', []):
                source = rel_data.get('source', '').strip()
                target = rel_data.get('target', '').strip()
                
                if source in merged_entities and target in merged_entities:
                    key = (source, target)
                    if key not in all_relations:
                        all_relations[key] = rel_data
        
        # 应用传递规则
        transitive_relations = []
        
        for (a, b), rel_ab in all_relations.items():
            for (c, d), rel_cd in all_relations.items():
                if b == c and a != d:  # A -> B, B -> D 推出 A -> D
                    transitive_rel = self._apply_transitive_rule(
                        a, b, d, rel_ab, rel_cd, merged_entities
                    )
                    if transitive_rel:
                        transitive_relations.append(transitive_rel)
        
        return transitive_relations
    
    def _apply_transitive_rule(self, 
                             entity_a: str, 
                             entity_b: str, 
                             entity_d: str,
                             rel_ab: Dict, 
                             rel_bd: Dict,
                             merged_entities: Dict[str, DynamicEntity]) -> Optional[DynamicRelationship]:
        """应用传递规则"""
        
        types_ab = rel_ab.get('types', []) or [rel_ab.get('relation_type', '')]
        types_bd = rel_bd.get('types', []) or [rel_bd.get('relation_type', '')]
        
        # 检查是否匹配推理规则
        for type_ab in types_ab:
            for type_bd in types_bd:
                rule_key = (type_ab.upper(), type_bd.upper())
                if rule_key in self.inference_rules:
                    new_type, base_confidence = self.inference_rules[rule_key]
                    
                    # 计算传递关系的置信度
                    conf_ab = rel_ab.get('confidence', 0.5)
                    conf_bd = rel_bd.get('confidence', 0.5)
                    transitive_confidence = base_confidence * conf_ab * conf_bd
                    
                    if transitive_confidence >= self.config.relation_confidence_threshold:
                        relationship = DynamicRelationship(
                            source_name=entity_a,
                            target_name=entity_d,
                            relationship_types=[new_type],
                            properties={
                                "discovery_method": "transitive_inference",
                                "intermediate_entity": entity_b,
                                "source_relation": type_ab,
                                "target_relation": type_bd,
                                "inference_confidence": transitive_confidence
                            },
                            confidence=transitive_confidence,
                            strength=transitive_confidence * 0.8
                        )
                        return relationship
        
        return None
    
    def _validate_relationships(self, 
                              relationships: List[DynamicRelationship],
                              merged_entities: Dict[str, DynamicEntity]) -> List[DynamicRelationship]:
        """验证和过滤关系"""
        
        validated = []
        
        for relationship in relationships:
            # 1. 置信度过滤
            if relationship.confidence < self.config.relation_confidence_threshold:
                continue
            
            # 2. 实体存在性检查
            if (relationship.source_name not in merged_entities or 
                relationship.target_name not in merged_entities):
                continue
            
            # 3. 避免自关联
            if relationship.source_name == relationship.target_name:
                continue
            
            # 4. 类型一致性检查
            if self._is_relationship_type_valid(relationship, merged_entities):
                validated.append(relationship)
        
        return validated
    
    def _is_relationship_type_valid(self, 
                                   relationship: DynamicRelationship,
                                   merged_entities: Dict[str, DynamicEntity]) -> bool:
        """检查关系类型是否与实体类型一致"""
        
        source_entity = merged_entities[relationship.source_name]
        target_entity = merged_entities[relationship.target_name]
        
        source_types = set(t.lower() for t in source_entity.types)
        target_types = set(t.lower() for t in target_entity.types)
        
        for rel_type in relationship.relationship_types:
            rel_type_lower = rel_type.lower()
            
            # 检查关系类型的合理性
            if "works_for" in rel_type_lower:
                if not (("person" in source_types) and 
                       ("organization" in target_types or "company" in target_types)):
                    return False
            
            elif "located_in" in rel_type_lower:
                if not (("location" in target_types) or 
                       ("organization" in source_types) or
                       ("person" in source_types)):
                    return False
            
            elif "created_by" in rel_type_lower:
                if not (("product" in source_types) and 
                       ("organization" in target_types or "person" in target_types)):
                    return False
        
        return True
    
    def get_discovery_statistics(self, relationships: List[DynamicRelationship]) -> Dict:
        """获取关系发现统计信息"""
        
        discovery_methods = defaultdict(int)
        relation_types = defaultdict(int)
        
        for rel in relationships:
            method = rel.properties.get("discovery_method", "unknown")
            discovery_methods[method] += 1
            
            for rel_type in rel.relationship_types:
                relation_types[rel_type] += 1
        
        return {
            "total_discovered": len(relationships),
            "discovery_methods": dict(discovery_methods),
            "relation_types": dict(relation_types),
            "average_confidence": sum(r.confidence for r in relationships) / len(relationships) if relationships else 0,
            "average_strength": sum(r.strength for r in relationships) / len(relationships) if relationships else 0
        }