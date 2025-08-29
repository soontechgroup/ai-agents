"""
Knowledge Node Model
Represents extracted knowledge from training sessions
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from neomodel import (
    StructuredNode, 
    StructuredRel,
    StringProperty, 
    FloatProperty, 
    DateTimeProperty,
    IntegerProperty,
    JSONProperty,
    RelationshipTo,
    RelationshipFrom,
    Relationship
)
from app.models.neomodel.base import BaseNode


class KnowledgeNode(BaseNode):
    """
    Knowledge node representing extracted facts, experiences, and learnings
    
    Knowledge differs from Memory:
    - Knowledge is extracted, structured information
    - Knowledge persists and doesn't decay
    - Knowledge can be validated and updated
    """
    
    # Core properties
    content = StringProperty(required=True, max_length=5000)
    summary = StringProperty(required=True, max_length=500)
    
    # Knowledge classification
    category = StringProperty(
        required=True,
        choices={
            'fact': 'Factual Information',
            'experience': 'Personal Experience', 
            'preference': 'Preference or Opinion',
            'skill': 'Skill or Capability',
            'rule': 'Rule or Guideline',
            'concept': 'Concept or Theory'
        }
    )
    
    # Source tracking
    source = StringProperty(
        required=True,
        choices={
            'training': 'Training Session',
            'conversation': 'Regular Conversation',
            'document': 'Document Import',
            'inference': 'Inferred from Other Knowledge'
        }
    )
    
    # Confidence and validation
    confidence = FloatProperty(default=0.8, min=0.0, max=1.0)
    validation_status = StringProperty(
        default='unvalidated',
        choices={
            'unvalidated': 'Not Yet Validated',
            'validated': 'Validated by User',
            'disputed': 'Disputed or Contradicted',
            'deprecated': 'Deprecated or Outdated'
        }
    )
    
    # Importance and usage
    importance = FloatProperty(default=0.5, min=0.0, max=1.0)
    access_count = IntegerProperty(default=0)
    usage_count = IntegerProperty(default=0)  # Times used in responses
    
    # Metadata
    keywords = JSONProperty(default=list)  # List of keywords
    context = JSONProperty(default=dict)  # Additional context
    embedding_id = StringProperty()  # Reference to vector embedding in Chroma
    
    # Digital human ownership
    digital_human_id = StringProperty(required=True, index=True)
    
    # Timestamps
    learned_at = DateTimeProperty(default_factory=datetime.now)
    last_accessed = DateTimeProperty()
    last_validated = DateTimeProperty()
    deprecated_at = DateTimeProperty()
    
    # Relationships
    # To other knowledge nodes
    related_to = Relationship(
        'KnowledgeNode', 
        'RELATED_TO',
        model=None  # Will be set after class definition
    )
    
    contradicts = Relationship(
        'KnowledgeNode',
        'CONTRADICTS', 
        model=None  # Will be set after class definition
    )
    
    supports = RelationshipTo(
        'KnowledgeNode',
        'SUPPORTS'
    )
    
    # To entities
    mentions_entities = RelationshipTo(
        'app.models.neomodel.entity.EntityNode',
        'MENTIONS'
    )
    
    # To memories (knowledge can be derived from memories)
    # TODO: Uncomment when MemoryNode is implemented
    # derived_from_memories = RelationshipTo(
    #     'app.models.neomodel.memory.MemoryNode',
    #     'DERIVED_FROM'
    # )
    
    # To digital human
    # TODO: Uncomment when DigitalHumanNode is implemented
    # learned_by = RelationshipTo(
    #     'app.models.neomodel.digital_human.DigitalHumanNode',
    #     'LEARNED_BY'
    # )
    
    # From user (who taught this)
    # TODO: Uncomment when UserNode is implemented
    # taught_by = RelationshipFrom(
    #     'app.models.neomodel.user.UserNode',
    #     'TAUGHT'
    # )
    
    def __str__(self):
        return f"Knowledge({self.category}): {self.summary[:50]}..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'uid': self.uid,
            'content': self.content,
            'summary': self.summary,
            'category': self.category,
            'source': self.source,
            'confidence': self.confidence,
            'validation_status': self.validation_status,
            'importance': self.importance,
            'access_count': self.access_count,
            'usage_count': self.usage_count,
            'keywords': self.keywords or [],
            'context': self.context or {},
            'digital_human_id': self.digital_human_id,
            'learned_at': self.learned_at.isoformat() if self.learned_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'last_validated': self.last_validated.isoformat() if self.last_validated else None
        }
    
    def update_access(self):
        """Update access count and timestamp"""
        self.access_count = (self.access_count or 0) + 1
        self.last_accessed = datetime.now()
        self.save()
    
    def update_usage(self):
        """Update usage count when used in a response"""
        self.usage_count = (self.usage_count or 0) + 1
        self.update_access()
    
    def validate(self, confidence: float = 1.0):
        """Mark as validated by user"""
        self.validation_status = 'validated'
        self.confidence = confidence
        self.last_validated = datetime.now()
        self.save()
    
    def dispute(self, reason: Optional[str] = None):
        """Mark as disputed"""
        self.validation_status = 'disputed'
        if reason and self.context:
            self.context['dispute_reason'] = reason
        self.save()
    
    def deprecate(self, replacement_uid: Optional[str] = None):
        """Mark as deprecated"""
        self.validation_status = 'deprecated'
        self.deprecated_at = datetime.now()
        if replacement_uid and self.context:
            self.context['replaced_by'] = replacement_uid
        self.save()


class KnowledgeRelationship(StructuredRel):
    """Relationship between knowledge nodes"""
    
    strength = FloatProperty(default=0.5, min=0.0, max=1.0)
    relation_type = StringProperty(
        choices={
            'prerequisite': 'Prerequisite',
            'consequence': 'Consequence',
            'example': 'Example',
            'generalization': 'Generalization',
            'specialization': 'Specialization'
        }
    )


class ContradictionRelationship(StructuredRel):
    """Relationship for contradicting knowledge"""
    
    reason = StringProperty()
    detected_at = DateTimeProperty(default_factory=datetime.now)
    resolved = StringProperty(
        choices={
            'unresolved': 'Not Resolved',
            'first_correct': 'First Knowledge Correct',
            'second_correct': 'Second Knowledge Correct',
            'both_contextual': 'Both Valid in Different Contexts'
        },
        default='unresolved'
    )


# Set relationship models after class definitions
KnowledgeNode.related_to.model = KnowledgeRelationship
KnowledgeNode.contradicts.model = ContradictionRelationship