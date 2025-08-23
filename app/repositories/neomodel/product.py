"""
产品仓储
"""

from typing import Optional, List

from app.models.neomodel.nodes import Product
from app.repositories.neomodel.base import NeomodelRepository


class ProductRepository(NeomodelRepository):
    """产品仓储"""
    
    def __init__(self):
        super().__init__(Product)
    
    def find_by_sku(self, sku: str) -> Optional[Product]:
        """通过SKU查找"""
        return self.find_by_property(sku=sku)
    
    def find_by_category(self, category: str) -> List[Product]:
        """通过分类查找"""
        return self.find_all(category=category)
    
    def find_by_brand(self, brand: str) -> List[Product]:
        """通过品牌查找"""
        return self.find_all(brand=brand)
    
    def find_in_stock(self) -> List[Product]:
        """查找有库存的产品"""
        products = self.find_all()
        return [p for p in products if p.stock > 0]