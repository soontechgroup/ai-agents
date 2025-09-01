"""
标签仓储
"""

from app.models.neomodel.nodes import Tag
from app.repositories.neomodel.base import NeomodelRepository


class TagRepository(NeomodelRepository):
    """标签仓储"""
    
    def __init__(self):
        super().__init__(Tag)
    
    def find_by_category(self, category: str) -> list:
        """按分类查找标签"""
        return self.find_all(category=category)