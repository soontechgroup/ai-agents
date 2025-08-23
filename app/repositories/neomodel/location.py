"""
地点仓储
"""

from typing import List
from datetime import datetime
from neomodel import db

from app.models.neomodel.nodes import Location
from app.repositories.neomodel.base import NeomodelRepository


class LocationRepository(NeomodelRepository):
    """地点仓储"""
    
    def __init__(self):
        super().__init__(Location)
    
    def find_by_type(self, location_type: str) -> List[Location]:
        """通过类型查找地点"""
        return self.find_all(location_type=location_type)
    
    def find_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10
    ) -> List[Location]:
        """查找附近的地点（需要Neo4j空间索引支持）"""
        query = """
            MATCH (l:Location)
            WHERE point.distance(
                point({latitude: l.latitude, longitude: l.longitude}),
                point({latitude: $lat, longitude: $lon})
            ) <= $radius * 1000
            RETURN l
        """
        try:
            results, _ = db.cypher_query(
                query,
                {"lat": latitude, "lon": longitude, "radius": radius_km}
            )
            return [Location.inflate(row[0]) for row in results]
        except:
            # 如果空间函数不可用，返回空列表
            return []
    
    def get_location_tree(self, root_uid: str = None) -> List[Dict]:
        """获取地点层级树"""
        if root_uid:
            root = self.find_by_uid(root_uid)
            if root and hasattr(root, 'contains'):
                children = list(root.contains.all())
                return [{
                    "location": child.to_dict(),
                    "children": self.get_location_tree(child.uid)
                } for child in children]
        else:
            # 获取顶级地点
            countries = self.find_all(location_type='country')
            return [{
                "location": country.to_dict(),
                "children": self.get_location_tree(country.uid)
            } for country in countries]
        return []