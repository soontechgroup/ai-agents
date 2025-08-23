"""
图数据库服务层
使用Neomodel ORM提供业务逻辑
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from app.repositories.neomodel import (
    PersonRepository,
    OrganizationRepository,
    LocationRepository,
    EventRepository,
    ProjectRepository,
    ProductRepository
)
from app.models.graph.nodes import PersonNode, OrganizationNode, LocationNode
from app.models.graph.nodes.event import EventNode
from app.models.graph.nodes.project import ProjectNode
from app.models.graph.nodes.product import ProductNode
from app.models.converters.graph_converter import GraphModelConverter
from app.core.neomodel_config import transaction

logger = logging.getLogger(__name__)


class GraphService:
    """
    图数据库服务类
    提供业务逻辑和数据编排
    """
    
    def __init__(self):
        """初始化所有仓储"""
        self.person_repo = PersonRepository()
        self.org_repo = OrganizationRepository()
        self.location_repo = LocationRepository()
        self.event_repo = EventRepository()
        self.project_repo = ProjectRepository()
        self.product_repo = ProductRepository()
    
    # ==================== 人员相关 ====================
    
    async def create_person(self, person_data: PersonNode) -> PersonNode:
        """
        创建人员
        
        Args:
            person_data: Pydantic人员模型
        
        Returns:
            创建的人员模型
        """
        try:
            # Pydantic → Neomodel → 保存
            neomodel_person = person_data.to_neomodel()
            if neomodel_person:
                neomodel_person.save()
                logger.info(f"创建人员成功: {person_data.name}")
                # Neomodel → Pydantic
                return PersonNode.from_neomodel(neomodel_person)
            return None
        except Exception as e:
            logger.error(f"创建人员失败: {str(e)}")
            raise
    
    async def get_person(self, uid: str) -> Optional[PersonNode]:
        """获取人员"""
        person = self.person_repo.find_by_uid(uid)
        if person:
            return PersonNode.from_neomodel(person)
        return None
    
    async def update_person(self, uid: str, person_data: PersonNode) -> Optional[PersonNode]:
        """更新人员"""
        updated = self.person_repo.update_from_pydantic(uid, person_data)
        if updated:
            return PersonNode.from_neomodel(updated)
        return None
    
    async def delete_person(self, uid: str) -> bool:
        """删除人员"""
        return self.person_repo.delete(uid)
    
    async def search_persons(self, keyword: str) -> List[PersonNode]:
        """搜索人员"""
        persons = self.person_repo.search(keyword, ["name", "email", "occupation", "bio"])
        return [PersonNode.from_neomodel(p) for p in persons]
    
    async def get_person_network(self, uid: str, depth: int = 2) -> Dict[str, Any]:
        """获取人员社交网络"""
        try:
            person = self.person_repo.find_by_uid(uid)
            if not person:
                return None
            
            # 获取不同层级的关系
            colleagues = self.person_repo.find_colleagues(uid)
            network = self.person_repo.find_network(uid, depth)
            
            return {
                "person": PersonNode.from_neomodel(person),
                "colleagues": [PersonNode.from_neomodel(c) for c in colleagues],
                "network": [PersonNode.from_neomodel(n) for n in network],
                "stats": {
                    "colleague_count": len(colleagues),
                    "network_size": len(network)
                }
            }
        except Exception as e:
            logger.error(f"获取人员网络失败: {str(e)}")
            return None
    
    # ==================== 组织相关 ====================
    
    async def create_organization(self, org_data: OrganizationNode) -> OrganizationNode:
        """创建组织"""
        try:
            neomodel_org = org_data.to_neomodel()
            if neomodel_org:
                neomodel_org.save()
                logger.info(f"创建组织成功: {org_data.name}")
                return OrganizationNode.from_neomodel(neomodel_org)
            return None
        except Exception as e:
            logger.error(f"创建组织失败: {str(e)}")
            raise
    
    async def get_organization(self, uid: str) -> Optional[OrganizationNode]:
        """获取组织"""
        org = self.org_repo.find_by_uid(uid)
        if org:
            return OrganizationNode.from_neomodel(org)
        return None
    
    async def get_organization_with_employees(self, uid: str) -> Optional[Dict[str, Any]]:
        """获取组织及其员工"""
        result = self.org_repo.get_with_employees(uid)
        if result:
            # 转换员工为Pydantic模型
            employees = []
            for emp_dict in result['employees']:
                try:
                    # 从字典创建Pydantic模型
                    emp = PersonNode(**emp_dict)
                    employees.append(emp)
                except:
                    pass
            
            result['employees'] = employees
            return result
        return None
    
    # ==================== 关系管理 ====================
    
    async def add_employment(
        self,
        person_uid: str,
        org_uid: str,
        position: str,
        department: str = None
    ) -> bool:
        """添加雇佣关系"""
        try:
            person = self.person_repo.find_by_uid(person_uid)
            org = self.org_repo.find_by_uid(org_uid)
            
            if person and org:
                person.works_at.connect(org, {
                    'position': position,
                    'department': department,
                    'start_date': datetime.now(),
                    'is_current': True
                })
                logger.info(f"添加雇佣关系: {person_uid} -> {org_uid}")
                return True
            return False
        except Exception as e:
            logger.error(f"添加雇佣关系失败: {str(e)}")
            return False
    
    async def add_friendship(self, person1_uid: str, person2_uid: str) -> bool:
        """添加朋友关系"""
        try:
            person1 = self.person_repo.find_by_uid(person1_uid)
            person2 = self.person_repo.find_by_uid(person2_uid)
            
            if person1 and person2:
                # 双向关系
                person1.friends.connect(person2, {
                    'since': datetime.now(),
                    'mutual': True
                })
                person2.friends.connect(person1, {
                    'since': datetime.now(),
                    'mutual': True
                })
                logger.info(f"添加朋友关系: {person1_uid} <-> {person2_uid}")
                return True
            return False
        except Exception as e:
            logger.error(f"添加朋友关系失败: {str(e)}")
            return False
    
    # ==================== 批量操作 ====================
    
    async def import_persons_batch(self, persons_data: List[PersonNode]) -> List[PersonNode]:
        """批量导入人员"""
        try:
            created_persons = []
            
            with transaction():
                for person_data in persons_data:
                    neomodel_person = person_data.to_neomodel()
                    if neomodel_person:
                        neomodel_person.save()
                        created_persons.append(PersonNode.from_neomodel(neomodel_person))
            
            logger.info(f"批量导入{len(created_persons)}个人员")
            return created_persons
        except Exception as e:
            logger.error(f"批量导入失败: {str(e)}")
            return []
    
    # ==================== 分析功能 ====================
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            from neomodel import db
            
            # 统计各类节点数量
            stats_query = """
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """
            results, _ = db.cypher_query(stats_query)
            
            node_stats = {}
            for row in results:
                if row[0]:  # 确保label不为空
                    node_stats[row[0]] = row[1]
            
            # 统计关系数量
            rel_query = """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """
            rel_results, _ = db.cypher_query(rel_query)
            
            rel_stats = {}
            for row in rel_results:
                if row[0]:
                    rel_stats[row[0]] = row[1]
            
            return {
                "nodes": node_stats,
                "relationships": rel_stats,
                "total_nodes": sum(node_stats.values()),
                "total_relationships": sum(rel_stats.values())
            }
        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            return {
                "error": str(e),
                "nodes": {},
                "relationships": {},
                "total_nodes": 0,
                "total_relationships": 0
            }
    
    # ==================== 复杂查询 ====================
    
    async def find_shortest_path(self, from_uid: str, to_uid: str) -> Optional[List[Dict]]:
        """查找两个节点之间的最短路径"""
        try:
            from neomodel import db
            
            query = """
                MATCH path = shortestPath(
                    (from:Person {uid: $from_uid})-[*]-(to:Person {uid: $to_uid})
                )
                RETURN [n in nodes(path) | {uid: n.uid, name: n.name}] as nodes,
                       [r in relationships(path) | type(r)] as relationships
            """
            
            results, _ = db.cypher_query(
                query,
                {"from_uid": from_uid, "to_uid": to_uid}
            )
            
            if results:
                return {
                    "nodes": results[0][0],
                    "relationships": results[0][1],
                    "length": len(results[0][1])
                }
            return None
        except Exception as e:
            logger.error(f"查找最短路径失败: {str(e)}")
            return None