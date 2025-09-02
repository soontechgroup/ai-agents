from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.models.graph.dynamic_entity import DynamicEntity
from app.models.graph.dynamic_relationship import DynamicRelationship

logger = logging.getLogger(__name__)


class DynamicGraphFactory:
    
    @classmethod
    def create_entity(
        cls,
        name: str,
        context: Optional[str] = None,
        initial_types: Optional[List[str]] = None,
        initial_properties: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5
    ) -> DynamicEntity:
        entity = DynamicEntity(
            name=name,
            types=initial_types or [],
            properties=initial_properties or {},
            confidence=confidence
        )
        
        if context:
            entity.add_context({"context": context}, source="factory_creation")
        
        logger.info(f"创建动态实体: {name}")
        return entity
    
    @classmethod
    def create_relationship(
        cls,
        source_name: str,
        target_name: str,
        context: Optional[str] = None,
        initial_types: Optional[List[str]] = None,
        initial_properties: Optional[Dict[str, Any]] = None,
        bidirectional: bool = False,
        confidence: float = 0.5
    ) -> DynamicRelationship:
        relationship = DynamicRelationship(
            source_name=source_name,
            target_name=target_name,
            relationship_types=initial_types or [],
            properties=initial_properties or {},
            bidirectional=bidirectional,
            confidence=confidence
        )
        
        if context:
            relationship.add_context({"context": context})
        
        logger.info(f"创建动态关系: {source_name} -> {target_name}")
        return relationship
    
    @classmethod
    def infer_entity_from_context(
        cls,
        name: str,
        context: str
    ) -> DynamicEntity:
        entity = cls.create_entity(name, context=context)
        
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['公司', 'company', '企业', 'corporation']):
            entity.add_type('组织')
        if any(word in context_lower for word in ['人', 'person', 'ceo', '创始人', 'founder']):
            entity.add_type('人物')
        if any(word in context_lower for word in ['产品', 'product', '服务', 'service']):
            entity.add_type('产品')
        
        return entity
    
    @classmethod
    def infer_relationship_from_context(
        cls,
        source_name: str,
        target_name: str,
        context: str
    ) -> DynamicRelationship:
        relationship = cls.create_relationship(source_name, target_name, context=context)
        
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['工作', 'work', '就职', 'employ']):
            relationship.add_type('雇佣关系')
        if any(word in context_lower for word in ['朋友', 'friend', '友谊']):
            relationship.add_type('朋友关系')
        if any(word in context_lower for word in ['竞争', 'compete', '对手']):
            relationship.add_type('竞争关系')
        if any(word in context_lower for word in ['合作', 'partner', '协作']):
            relationship.add_type('合作关系')
        
        return relationship
    
    @classmethod
    def merge_entities(
        cls,
        entities: List[DynamicEntity],
        primary_name: str
    ) -> DynamicEntity:
        if not entities:
            return cls.create_entity(primary_name)
        
        primary = None
        for entity in entities:
            if entity.name == primary_name:
                primary = entity
                break
        
        if not primary:
            primary = entities[0]
            primary.name = primary_name
        
        for entity in entities:
            if entity != primary:
                primary.merge_with(entity)
        
        logger.info(f"合并 {len(entities)} 个实体为: {primary_name}")
        return primary
    
    @classmethod
    def create_from_extraction(
        cls,
        extraction_result: Dict[str, Any]
    ) -> tuple[List[DynamicEntity], List[DynamicRelationship]]:
        entities = []
        relationships = []
        
        for entity_data in extraction_result.get('entities', []):
            entity = cls.create_entity(
                name=entity_data.get('name'),
                initial_types=[entity_data.get('type')] if entity_data.get('type') else [],
                initial_properties={'description': entity_data.get('description')}
            )
            entities.append(entity)
        
        for rel_data in extraction_result.get('relationships', []):
            relationship = cls.create_relationship(
                source_name=rel_data.get('source'),
                target_name=rel_data.get('target'),
                initial_types=[rel_data.get('relation_type')] if rel_data.get('relation_type') else [],
                initial_properties={'description': rel_data.get('description')}
            )
            relationships.append(relationship)
        
        return entities, relationships


def create_entity(name: str, **kwargs) -> DynamicEntity:
    return DynamicGraphFactory.create_entity(name, **kwargs)


def create_relationship(source: str, target: str, **kwargs) -> DynamicRelationship:
    return DynamicGraphFactory.create_relationship(source, target, **kwargs)


def infer_from_context(name: str, context: str) -> DynamicEntity:
    return DynamicGraphFactory.infer_entity_from_context(name, context)