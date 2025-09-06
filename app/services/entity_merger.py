from typing import Dict, List, Optional, Set
import difflib
import logging
from datetime import datetime

from app.models.graph.dynamic_entity import DynamicEntity
from app.services.extraction_config import ExtractionConfig, ConfidenceMergeStrategy

logger = logging.getLogger(__name__)


class EntityMerger:
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        
        self.alias_patterns = {
            "company": [
                ("公司", "Co.", "Corp.", "Corporation", "Inc.", "Ltd.", "Limited"),
                ("科技", "Technology", "Tech"),
                ("集团", "Group"),
            ],
            "person": [
                ("先生", "Mr.", "Mr"),
                ("女士", "Ms.", "Miss", "Mrs."),
            ]
        }
    
    def merge_entities(self, entities: List[DynamicEntity]) -> Dict[str, DynamicEntity]:
        if not entities:
            return {}
        
        merged_entities = {}
        entity_groups = self._group_similar_entities(entities)
        
        for group in entity_groups:
            merged_entity = self._merge_entity_group(group)
            merged_entities[merged_entity.name] = merged_entity
            
            if self.config.enable_debug_logging:
                logger.debug(f"合并实体组: {[e.name for e in group]} -> {merged_entity.name}")
        
        return merged_entities
    
    def _group_similar_entities(self, entities: List[DynamicEntity]) -> List[List[DynamicEntity]]:
        groups = []
        used_entities = set()
        
        for i, entity in enumerate(entities):
            if i in used_entities:
                continue
            
            current_group = [entity]
            used_entities.add(i)
            
            for j, other_entity in enumerate(entities[i+1:], i+1):
                if j in used_entities:
                    continue
                    
                if self._are_entities_similar(entity, other_entity):
                    current_group.append(other_entity)
                    used_entities.add(j)
            
            groups.append(current_group)
        
        return groups
    
    def _are_entities_similar(self, entity1: DynamicEntity, entity2: DynamicEntity) -> bool:
        
        if entity1.name.lower() == entity2.name.lower():
            return True
        

        similarity = difflib.SequenceMatcher(None, 
                                           entity1.name.lower(), 
                                           entity2.name.lower()).ratio()
        if similarity >= self.config.entity_similarity_threshold:
            return True
        

        if self.config.enable_entity_aliasing:
            if self._are_aliases(entity1.name, entity2.name, entity1.types + entity2.types):
                return True
        
        if self._have_compatible_types(entity1, entity2):
            if similarity >= self.config.entity_similarity_threshold * 0.8:
                return True
        
        return False
    
    def _are_aliases(self, name1: str, name2: str, entity_types: List[str]) -> bool:
        
        clean_name1 = self._clean_entity_name(name1, entity_types)
        clean_name2 = self._clean_entity_name(name2, entity_types)
        
        if clean_name1.lower() == clean_name2.lower():
            return True
        
        # 检查是否一个名字包含另一个（如 "马斯克" 和 "埃隆·马斯克"）
        if clean_name1.lower() in clean_name2.lower() or clean_name2.lower() in clean_name1.lower():
            return True
        
        # 检查英文和中文混合的情况（如 "Elon Musk" 和 "马斯克"）
        # 简单的音译匹配
        transliteration_pairs = [
            ("musk", "马斯克"),
            ("elon", "埃隆"),
            ("jobs", "乔布斯"),
            ("cook", "库克"),
            ("gates", "盖茨"),
        ]
        
        for eng, chi in transliteration_pairs:
            if (eng in clean_name1.lower() and chi in clean_name2) or \
               (eng in clean_name2.lower() and chi in clean_name1):
                return True
        

        shorter, longer = (clean_name1, clean_name2) if len(clean_name1) < len(clean_name2) else (clean_name2, clean_name1)
        if len(shorter) >= 3 and shorter.lower() in longer.lower():
            return True
        
        return False
    
    def _clean_entity_name(self, name: str, entity_types: List[str]) -> str:
        cleaned = name.strip()
        

        type_lower = [t.lower() for t in entity_types]
        
        if any(t in ["organization", "company", "tech_company"] for t in type_lower):
            for pattern_group in self.alias_patterns.get("company", []):
                for suffix in pattern_group:
                    if cleaned.endswith(suffix):
                        cleaned = cleaned[:-len(suffix)].strip()
                        break
        
        elif any(t in ["person"] for t in type_lower):
            for pattern_group in self.alias_patterns.get("person", []):
                for suffix in pattern_group:
                    if suffix.lower() in cleaned.lower():
                        cleaned = cleaned.replace(suffix, "").strip()
        
        return cleaned
    
    def _have_compatible_types(self, entity1: DynamicEntity, entity2: DynamicEntity) -> bool:
        types1 = set(t.lower() for t in entity1.types)
        types2 = set(t.lower() for t in entity2.types)
        

        if types1 & types2:
            return True
        

        hierarchical_types = {
            "tech_company": {"organization", "company"},
            "software_engineer": {"person", "employee"},
            "ceo": {"person", "executive"},
            "startup_founder": {"person", "entrepreneur"}
        }
        
        for type1 in types1:
            if type1 in hierarchical_types:
                if types2 & hierarchical_types[type1]:
                    return True
        
        for type2 in types2:
            if type2 in hierarchical_types:
                if types1 & hierarchical_types[type2]:
                    return True
        
        return False
    
    def _merge_entity_group(self, entities: List[DynamicEntity]) -> DynamicEntity:
        if len(entities) == 1:
            return entities[0]
        

        primary_entity = max(entities, key=lambda e: e.confidence)
        

        for entity in entities:
            if entity != primary_entity:
                self._merge_single_entity(primary_entity, entity)
        

        primary_entity.updated_at = datetime.now()
        
        return primary_entity
    
    def _merge_single_entity(self, primary: DynamicEntity, secondary: DynamicEntity) -> None:
        
        for entity_type in secondary.types:
            primary.add_type(entity_type)
        

        for key, value in secondary.properties.items():
            secondary_confidence = secondary.property_confidence.get(key, 0.5)
            primary_confidence = primary.property_confidence.get(key, 0.0)
            
            if key not in primary.properties:
                primary.set_property(key, value, secondary_confidence)
            else:
                self._resolve_property_conflict(primary, key, value, 
                                              primary_confidence, secondary_confidence)
        

        primary.contexts.extend(secondary.contexts)
        for source in secondary.sources:
            if source not in primary.sources:
                primary.sources.append(source)
        

        if self.config.confidence_merge_strategy == ConfidenceMergeStrategy.MAX:
            primary.confidence = max(primary.confidence, secondary.confidence)
        elif self.config.confidence_merge_strategy == ConfidenceMergeStrategy.WEIGHTED_AVG:
            total_props = len(primary.properties) + len(secondary.properties)
            if total_props > 0:
                weight_primary = len(primary.properties) / total_props
                weight_secondary = len(secondary.properties) / total_props
                primary.confidence = (primary.confidence * weight_primary + 
                                    secondary.confidence * weight_secondary)
        elif self.config.confidence_merge_strategy == ConfidenceMergeStrategy.ACCUMULATE:
            primary.confidence = min(1.0, primary.confidence + secondary.confidence * 0.1)
    
    def _resolve_property_conflict(self, entity: DynamicEntity, key: str, new_value,
                                  current_confidence: float, new_confidence: float) -> None:
        
        if new_confidence > current_confidence:
            old_value = entity.properties[key]
            entity.set_property(key, new_value, new_confidence)
            entity.record_change(key, old_value, new_value)
        elif new_confidence == current_confidence and entity.properties[key] != new_value:
            merged_value = self._merge_property_values(entity.properties[key], new_value, key)
            if merged_value != entity.properties[key]:
                entity.set_property(key, merged_value, current_confidence)
    
    def _merge_property_values(self, current_value, new_value, property_key: str):
        
        if isinstance(current_value, list) and isinstance(new_value, list):
            merged = list(set(current_value + new_value))
            return merged
        

        if isinstance(current_value, str) and isinstance(new_value, str):
            if len(new_value) > len(current_value):
                return new_value
        

        return current_value
    
    def get_merge_statistics(self, original_count: int, merged_count: int) -> Dict:
        return {
            "original_entities": original_count,
            "merged_entities": merged_count,
            "merge_ratio": (original_count - merged_count) / original_count if original_count > 0 else 0,
            "entities_saved": original_count - merged_count
        }