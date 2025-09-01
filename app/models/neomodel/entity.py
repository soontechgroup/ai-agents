"""
Entity Node Model
Represents entities mentioned in knowledge and memories
"""

from datetime import datetime
from typing import Dict, Any
from neomodel import (
    StructuredNode,
    StructuredRel,
    StringProperty,
    IntegerProperty,
    FloatProperty,
    DateTimeProperty,
    JSONProperty,
    RelationshipFrom,
    RelationshipTo,
    Relationship
)
from app.models.neomodel.base import BaseNode


class EntityNode(BaseNode):
    """
    Entity node representing people, places, concepts, etc. mentioned in knowledge
    
    Entities serve as connection points between different pieces of knowledge
    """
    
    # Core properties
    name = StringProperty(required=True, index=True, max_length=200)
    entity_type = StringProperty(
        required=True,
        choices={
            'person': 'Person',
            'place': 'Place',
            'organization': 'Organization',
            'concept': 'Concept',
            'technology': 'Technology',
            'event': 'Event',
            'product': 'Product',
            'other': 'Other'
        }
    )
    
    # Description and context
    description = StringProperty(max_length=1000)
    aliases = JSONProperty(default=list)  # Alternative names
    attributes = JSONProperty(default=dict)  # Key attributes
    
    # Usage tracking
    mention_count = IntegerProperty(default=1)
    importance_score = FloatProperty(default=0.5, min=0.0, max=1.0)
    
    # Digital human context
    digital_human_id = StringProperty(required=True, index=True)
    
    # Timestamps
    first_mentioned = DateTimeProperty(default_factory=datetime.now)
    last_mentioned = DateTimeProperty(default_factory=datetime.now)
    
    # Relationships
    # From knowledge nodes
    mentioned_in_knowledge = RelationshipFrom(
        'app.models.neomodel.knowledge.KnowledgeNode',
        'MENTIONS'
    )
    
    # From memory nodes
    # TODO: Uncomment when MemoryNode is implemented
    # mentioned_in_memories = RelationshipFrom(
    #     'app.models.neomodel.memory.MemoryNode',
    #     'MENTIONS'
    # )
    
    # Co-occurrence with other entities
    co_occurs_with = Relationship(
        'EntityNode',
        'CO_OCCURS',
        model=None  # Will be set after class definition
    )
    
    # Hierarchical relationships
    parent_of = RelationshipTo(
        'EntityNode',
        'PARENT_OF'
    )
    
    child_of = RelationshipFrom(
        'EntityNode',
        'PARENT_OF'
    )
    
    def __str__(self):
        return f"Entity({self.entity_type}): {self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'uid': self.uid,
            'name': self.name,
            'entity_type': self.entity_type,
            'description': self.description,
            'aliases': self.aliases or [],
            'attributes': self.attributes or {},
            'mention_count': self.mention_count,
            'importance_score': self.importance_score,
            'digital_human_id': self.digital_human_id,
            'first_mentioned': self.first_mentioned.isoformat() if self.first_mentioned else None,
            'last_mentioned': self.last_mentioned.isoformat() if self.last_mentioned else None
        }
    
    def update_mention(self):
        """Update mention count and timestamp"""
        self.mention_count = (self.mention_count or 0) + 1
        self.last_mentioned = datetime.now()
        self.save()
    
    def add_alias(self, alias: str):
        """Add an alternative name for this entity"""
        if not self.aliases:
            self.aliases = []
        if alias not in self.aliases:
            self.aliases.append(alias)
            self.save()
    
    def set_attribute(self, key: str, value: Any):
        """Set an attribute for this entity"""
        if not self.attributes:
            self.attributes = {}
        self.attributes[key] = value
        self.save()
    
    def merge_with(self, other_entity: 'EntityNode'):
        """
        Merge another entity into this one
        Used when detecting duplicate entities
        """
        # Merge aliases
        if other_entity.aliases:
            for alias in other_entity.aliases:
                self.add_alias(alias)
        
        # Merge attributes
        if other_entity.attributes:
            for key, value in other_entity.attributes.items():
                if key not in self.attributes:
                    self.set_attribute(key, value)
        
        # Update mention count
        self.mention_count += other_entity.mention_count
        
        # Update importance (take maximum)
        self.importance_score = max(
            self.importance_score or 0.5,
            other_entity.importance_score or 0.5
        )
        
        # Keep earliest first mention
        if other_entity.first_mentioned and self.first_mentioned:
            self.first_mentioned = min(
                self.first_mentioned,
                other_entity.first_mentioned
            )
        
        # Keep latest last mention
        if other_entity.last_mentioned and self.last_mentioned:
            self.last_mentioned = max(
                self.last_mentioned,
                other_entity.last_mentioned
            )
        
        self.save()


class CoOccurrenceRelationship(StructuredRel):
    """Relationship between entities that appear together"""
    
    occurrence_count = IntegerProperty(default=1)
    correlation_strength = FloatProperty(default=0.5, min=0.0, max=1.0)
    first_seen = DateTimeProperty(default_factory=datetime.now)
    last_seen = DateTimeProperty(default_factory=datetime.now)
    
    def update_occurrence(self):
        """Update co-occurrence statistics"""
        self.occurrence_count = (self.occurrence_count or 0) + 1
        self.last_seen = datetime.now()
        # Increase correlation strength with more co-occurrences
        self.correlation_strength = min(
            1.0,
            0.5 + (self.occurrence_count * 0.05)
        )
        self.save()


# Set relationship model after class definition
EntityNode.co_occurs_with.model = CoOccurrenceRelationship