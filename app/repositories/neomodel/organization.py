"""
组织仓储
"""

from typing import List, Optional, Dict, Any

from app.models.neomodel.nodes import Organization
from app.repositories.neomodel.base import NeomodelRepository


class OrganizationRepository(NeomodelRepository):
    """组织仓储"""
    
    def __init__(self):
        super().__init__(Organization)
    
    def find_by_industry(self, industry: str) -> List[Organization]:
        """通过行业查找"""
        return self.find_all(industry=industry)
    
    def find_by_name(self, name: str) -> Optional[Organization]:
        """通过名称查找"""
        return self.find_by_property(name=name)
    
    def get_with_employees(self, uid: str) -> Optional[Dict[str, Any]]:
        """获取组织及其员工"""
        org = self.find_by_uid(uid)
        if org:
            employees = list(org.employees.all())
            return {
                "organization": org.to_dict(),
                "employees": [emp.to_dict() for emp in employees],
                "employee_count": len(employees)
            }
        return None
    
    def get_hierarchy(self, uid: str) -> Dict[str, Any]:
        """获取组织层级结构"""
        org = self.find_by_uid(uid)
        if org:
            parent = org.parent_org.single() if hasattr(org, 'parent_org') else None
            subsidiaries = list(org.subsidiaries.all()) if hasattr(org, 'subsidiaries') else []
            
            return {
                "organization": org.to_dict(),
                "parent": parent.to_dict() if parent else None,
                "subsidiaries": [sub.to_dict() for sub in subsidiaries]
            }
        return None