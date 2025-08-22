"""
节点模型包
"""

from app.models.graph.nodes.person import PersonNode
from app.models.graph.nodes.organization import OrganizationNode

__all__ = [
    "PersonNode",
    "OrganizationNode",
]