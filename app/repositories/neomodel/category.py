"""
分类仓储
"""

from typing import List, Dict, Optional

from app.models.neomodel.nodes import Category
from app.repositories.neomodel.base import NeomodelRepository


class CategoryRepository(NeomodelRepository):
    """分类仓储"""
    
    def __init__(self):
        super().__init__(Category)
    
    def get_tree(self, parent_uid: Optional[str] = None) -> List[Dict]:
        """获取分类树"""
        if parent_uid:
            parent = self.find_by_uid(parent_uid)
            if parent and hasattr(parent, 'children'):
                children = list(parent.children.all())
                return [
                    {
                        "category": child.to_dict(),
                        "children": self.get_tree(child.uid)
                    }
                    for child in children
                ]
        else:
            # 获取顶级分类
            roots = self.find_all(level=0)
            return [
                {
                    "category": root.to_dict(),
                    "children": self.get_tree(root.uid)
                }
                for root in roots
            ]
        return []