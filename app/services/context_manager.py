from typing import Dict, List, Set, Optional, Tuple
import logging
from collections import Counter

from app.models.graph.dynamic_entity import DynamicEntity
from app.services.extraction_config import ExtractionConfig

logger = logging.getLogger(__name__)


class ContextManager:
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        
        self.global_entities = {}
        self.entity_mentions = Counter()
        self.chunk_history = []
        
        self.key_entities = set()
        self.entity_types_counter = Counter()
    
    def build_chunk_context(self, chunk_text: str, chunk_index: int) -> str:
        if not self.config.enable_context_enhancement or chunk_index == 0:
            return chunk_text
        
        context_info = self._generate_context_info(chunk_index)
        
        if not context_info:
            return chunk_text
        
        enhanced_prompt = f"""
## 上下文信息
在前面的文本中，我们已经识别出以下重要实体和信息：

{context_info}

## 当前文本块
请基于上述上下文信息，分析以下文本中的实体和关系。特别注意：
1. 是否有与上述实体相关的新信息
2. 是否存在跨文本块的关系
3. 保持实体命名的一致性

{chunk_text}
"""
        
        if self.config.enable_debug_logging:
            logger.debug(f"为块 {chunk_index} 生成上下文增强，包含 {len(self.key_entities)} 个关键实体")
        
        return enhanced_prompt
    
    def update_context(self, chunk_index: int, chunk_result: Dict, merged_entities: Dict[str, DynamicEntity]) -> None:
        self.global_entities.update(merged_entities)
        

        chunk_entity_names = []
        for entity_data in chunk_result.get('entities', []):
            entity_name = entity_data.get('name', '').strip()
            if entity_name:
                self.entity_mentions[entity_name] += 1
                chunk_entity_names.append(entity_name)
        

        for entity in merged_entities.values():
            for entity_type in entity.types:
                self.entity_types_counter[entity_type.lower()] += 1
        

        self._update_key_entities()
        

        self.chunk_history.append({
            "chunk_index": chunk_index,
            "entities_found": len(chunk_result.get('entities', [])),
            "relationships_found": len(chunk_result.get('relationships', [])),
            "processing_time": chunk_result.get('processing_time', 0),
            "entity_names": chunk_entity_names
        })
    
    def _generate_context_info(self, current_chunk_index: int) -> str:
        
        if not self.key_entities:
            return ""
        
        context_parts = []
        

        entity_info = self._get_key_entities_info()
        if entity_info:
            context_parts.append(f"### 重要实体\n{entity_info}")
        

        type_info = self._get_entity_type_distribution()
        if type_info:
            context_parts.append(f"### 实体类型分布\n{type_info}")
        

        recent_entities = self._get_recent_entities(current_chunk_index)
        if recent_entities:
            context_parts.append(f"### 最近提及的实体\n{recent_entities}")
        
        return "\n\n".join(context_parts)
    
    def _get_key_entities_info(self) -> str:
        
        top_entities = []
        for entity_name in list(self.key_entities)[:self.config.max_context_entities]:
            if entity_name in self.global_entities:
                entity = self.global_entities[entity_name]
                mention_count = self.entity_mentions[entity_name]
                types_str = ", ".join(entity.types[:3])
                

                key_props = []
                for key, value in entity.properties.items():
                    if key in ["company", "role", "location", "industry", "type"]:
                        key_props.append(f"{key}: {value}")
                
                props_str = " | ".join(key_props[:2]) if key_props else ""
                
                entity_desc = f"- **{entity_name}** ({types_str})"
                if props_str:
                    entity_desc += f" - {props_str}"
                entity_desc += f" [提及 {mention_count} 次]"
                
                top_entities.append(entity_desc)
        
        return "\n".join(top_entities)
    
    def _get_entity_type_distribution(self) -> str:
        
        top_types = self.entity_types_counter.most_common(5)
        type_lines = []
        
        for entity_type, count in top_types:
            type_lines.append(f"- {entity_type.upper()}: {count} 个")
        
        return "\n".join(type_lines)
    
    def _get_recent_entities(self, current_chunk_index: int) -> str:
        
        if current_chunk_index < self.config.context_window_size:
            return ""
        

        start_index = max(0, current_chunk_index - self.config.context_window_size)
        recent_chunks = self.chunk_history[start_index:current_chunk_index]
        
        recent_entity_counter = Counter()
        for chunk_info in recent_chunks:
            entity_names = chunk_info.get('entity_names', [])
            for entity_name in entity_names:
                recent_entity_counter[entity_name] += 1
        
        
        if not recent_entity_counter:
            recent_entities = []
            for entity_name, count in self.entity_mentions.most_common(5):
                if entity_name in self.global_entities:
                    entity = self.global_entities[entity_name]
                    types_str = ", ".join(entity.types[:2])
                    recent_entities.append(f"- {entity_name} ({types_str})")
            return "\n".join(recent_entities)
        
        recent_entities = []
        for entity_name, recent_count in recent_entity_counter.most_common(5):
            if entity_name in self.global_entities:
                entity = self.global_entities[entity_name]
                types_str = ", ".join(entity.types[:2])
                recent_entities.append(f"- {entity_name} ({types_str})")
        
        return "\n".join(recent_entities)
    
    def _update_key_entities(self) -> None:
        
        entity_scores = {}
        
        for entity_name, entity in self.global_entities.items():
            score = 0
            

            mention_count = self.entity_mentions[entity_name]
            score += mention_count * 0.3
            

            score += entity.confidence * 0.3
            

            score += len(entity.properties) * 0.2
            

            important_types = {"person", "organization", "company", "tech_company", "ceo"}
            for entity_type in entity.types:
                if entity_type.lower() in important_types:
                    score += 0.2
                    break
            
            entity_scores[entity_name] = score
        

        sorted_entities = sorted(entity_scores.items(), key=lambda x: x[1], reverse=True)
        self.key_entities = set(name for name, score in sorted_entities[:self.config.max_context_entities])
    
    def get_context_statistics(self) -> Dict:
        return {
            "total_entities": len(self.global_entities),
            "key_entities_count": len(self.key_entities),
            "chunks_processed": len(self.chunk_history),
            "most_mentioned_entities": dict(self.entity_mentions.most_common(10)),
            "entity_type_distribution": dict(self.entity_types_counter.most_common(10)),
            "average_entities_per_chunk": (
                sum(chunk["entities_found"] for chunk in self.chunk_history) / 
                len(self.chunk_history) if self.chunk_history else 0
            )
        }
    
    def should_include_entity_in_context(self, entity_name: str) -> bool:
        
        if entity_name in self.key_entities:
            return True
        

        if self.entity_mentions[entity_name] >= 2:
            return True
        
        if (entity_name in self.global_entities and 
            self.global_entities[entity_name].confidence >= 0.8):
            return True
        
        return False
    
    def get_entity_context_summary(self, entity_name: str) -> Optional[str]:
        
        if entity_name not in self.global_entities:
            return None
        
        entity = self.global_entities[entity_name]
        mention_count = self.entity_mentions[entity_name]
        
        summary_parts = [
            f"实体: {entity_name}",
            f"类型: {', '.join(entity.types)}",
            f"置信度: {entity.confidence:.2f}",
            f"提及次数: {mention_count}"
        ]
        
        if entity.properties:
            key_props = []
            for key, value in list(entity.properties.items())[:3]:
                key_props.append(f"{key}: {value}")
            if key_props:
                summary_parts.append(f"属性: {'; '.join(key_props)}")
        
        return " | ".join(summary_parts)
    
    def clear_context(self) -> None:
        self.global_entities.clear()
        self.entity_mentions.clear()
        self.chunk_history.clear()
        self.key_entities.clear()
        self.entity_types_counter.clear()
        
        logger.info("上下文状态已清理")