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
            # 支持新的多类型和结构化属性格式
            types = entity_data.get('types', [])
            if not types and entity_data.get('type'):
                # 向后兼容：处理旧的单一类型格式
                types = [t.strip() for t in entity_data['type'].split('|') if t.strip()]
            
            properties = entity_data.get('properties', {})
            # 如果没有结构化属性，使用描述作为属性
            if not properties and entity_data.get('description'):
                properties = {'description': entity_data.get('description')}
            
            entity = cls.create_entity(
                name=entity_data.get('name', ''),
                initial_types=types,
                initial_properties=properties,
                confidence=entity_data.get('confidence', 0.5)
            )
            
            # 设置置信度和其他元数据
            entity.confidence = entity_data.get('confidence', 0.5)
            entities.append(entity)
            
            logger.info(f"创建实体: {entity.name} 类型: {entity.types} 置信度: {entity.confidence}")
        
        for rel_data in extraction_result.get('relationships', []):
            # 支持新的多类型和结构化属性格式
            types = rel_data.get('types', [])
            if not types and rel_data.get('relation_type'):
                # 向后兼容：处理旧的单一类型格式
                types = [t.strip() for t in rel_data['relation_type'].split('|') if t.strip()]
            
            properties = rel_data.get('properties', {})
            # 如果没有结构化属性，使用描述作为属性
            if not properties and rel_data.get('description'):
                properties = {'description': rel_data.get('description')}
            
            relationship = cls.create_relationship(
                source_name=rel_data.get('source', ''),
                target_name=rel_data.get('target', ''),
                initial_types=types,
                initial_properties=properties,
                confidence=rel_data.get('confidence', 0.5)
            )
            
            # 设置关系的置信度和强度
            relationship.confidence = rel_data.get('confidence', 0.5)
            relationship.strength = rel_data.get('strength', 0.5)
            relationships.append(relationship)
            
            logger.info(f"创建关系: {relationship.source_name} -> {relationship.target_name} "
                       f"类型: {relationship.relationship_types} 置信度: {relationship.confidence}")
        
        return entities, relationships


def create_entity(name: str, **kwargs) -> DynamicEntity:
    return DynamicGraphFactory.create_entity(name, **kwargs)


def create_relationship(source: str, target: str, **kwargs) -> DynamicRelationship:
    return DynamicGraphFactory.create_relationship(source, target, **kwargs)


def infer_from_context(name: str, context: str) -> DynamicEntity:
    return DynamicGraphFactory.infer_entity_from_context(name, context)