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
    ProductRepository,
    GraphRepository
)
from app.models.graph.nodes import PersonNode, OrganizationNode
# TODO: 以下模型尚未实现
# from app.models.graph.nodes import LocationNode
# from app.models.graph.nodes.event import EventNode
# from app.models.graph.nodes.project import ProjectNode
# from app.models.graph.nodes.product import ProductNode

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
        self.graph_repo = GraphRepository()
    
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
            # 使用仓储层创建
            neomodel_person = self.person_repo.create_from_pydantic(person_data)
            if neomodel_person:
                logger.info(f"创建人员成功: {person_data.name}")
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
            # 使用仓储层创建
            neomodel_org = self.org_repo.create_from_pydantic(org_data)
            if neomodel_org:
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
                # 创建工作关系，属性会使用默认值
                rel = person.works_at.connect(org)
                # 更新关系属性
                if rel:
                    rel.position = position
                    rel.department = department
                    rel.save()
                logger.info(f"添加雇佣关系: {person_uid} -> {org_uid}")
                return True
            return False
        except Exception as e:
            logger.error(f"添加雇佣关系失败: {str(e)}")
            return False
    
    async def add_friendship(self, person1_identifier: str, person2_identifier: str) -> bool:
        """
        添加朋友关系
        
        Args:
            person1_identifier: 第一个人的UID或名字
            person2_identifier: 第二个人的UID或名字
            
        Returns:
            bool: 是否成功添加关系
        """
        logger.info(f"服务层: 进入add_friendship方法")
        try:
            import re
            
            # UUID模式匹配
            uuid_pattern = re.compile(r'^[a-f0-9]{32}$')
            
            # 处理第一个人物标识
            person1_uid = person1_identifier
            if not uuid_pattern.match(person1_identifier):
                # 可能是名字，尝试查找
                persons = self.person_repo.find_by_name(person1_identifier)
                if persons:
                    person1_uid = persons[0].uid
                    logger.info(f"服务层: 将名字 {person1_identifier} 转换为UID: {person1_uid}")
                else:
                    logger.error(f"服务层: 找不到人物: {person1_identifier}")
                    return False
            
            # 处理第二个人物标识
            person2_uid = person2_identifier
            if not uuid_pattern.match(person2_identifier):
                # 可能是名字，尝试查找
                persons = self.person_repo.find_by_name(person2_identifier)
                if persons:
                    person2_uid = persons[0].uid
                    logger.info(f"服务层: 将名字 {person2_identifier} 转换为UID: {person2_uid}")
                else:
                    logger.error(f"服务层: 找不到人物: {person2_identifier}")
                    return False
            
            logger.info(f"服务层: 开始添加朋友关系 {person1_uid} <-> {person2_uid}")
            
            # 查找人物节点
            person1 = self.person_repo.find_by_uid(person1_uid)
            person2 = self.person_repo.find_by_uid(person2_uid)
            
            if not person1:
                logger.error(f"服务层: UID {person1_uid} 对应的人物不存在")
                return False
            
            if not person2:
                logger.error(f"服务层: UID {person2_uid} 对应的人物不存在")
                return False
            
            logger.info(f"服务层: 找到两个人物 - {person1.name} 和 {person2.name}")
            
            try:
                # 检查friends属性是否存在
                if not hasattr(person1, 'friends'):
                    logger.error(f"服务层: Person1没有friends属性")
                    return False
                
                # Relationship是双向的，只需要连接一次
                rel = person1.friends.connect(person2)
                
                if rel:
                    rel.save()
                    logger.info(f"服务层: 成功添加朋友关系: {person1.name} <-> {person2.name}")
                    return True
                
                return False
                
            except AttributeError as ae:
                logger.error(f"服务层: 属性错误 - {str(ae)}")
                return False
            except Exception as inner_e:
                logger.error(f"服务层: 连接关系时出错 - {str(inner_e)}")
                return False
            
        except Exception as e:
            logger.exception(f"服务层: 添加朋友关系异常: {str(e)}")
            return False
    
    # ==================== 分析功能 ====================
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return self.graph_repo.get_statistics()
    
    # ==================== 复杂查询 ====================
    
    async def find_shortest_path(self, from_uid: str, to_uid: str) -> Optional[Dict[str, Any]]:
        """查找两个节点之间的最短路径"""
        return self.graph_repo.find_shortest_path(from_uid, to_uid)
    
    async def list_relationships(self, relationship_type: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        获取图数据库中的所有关系
        
        Args:
            relationship_type: 可选的关系类型过滤
            limit: 返回数量限制
            
        Returns:
            包含关系列表和总数的字典
        """
        return self.graph_repo.list_all_relationships(relationship_type, limit)