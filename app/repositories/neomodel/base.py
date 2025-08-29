"""
Neomodel仓储基类
提供通用的CRUD操作
"""

from typing import List, Dict, Any, Optional, Type
import logging
from datetime import datetime

from neomodel import db, StructuredNode
from neomodel.exceptions import DoesNotExist

from app.models.neomodel.base import BaseNode
from app.models.converters.graph_converter import GraphModelConverter
from app.core.neomodel_config import transaction

logger = logging.getLogger(__name__)


class NeomodelRepository:
    """
    Neomodel仓储基类
    提供通用的CRUD操作
    """
    
    def __init__(self, model_class: Type[BaseNode]):
        """
        初始化仓储
        
        Args:
            model_class: Neomodel模型类
        """
        self.model_class = model_class
        self.model_name = model_class.__name__
    
    # ==================== 创建操作 ====================
    
    def create(self, **properties) -> Optional[BaseNode]:
        """
        创建单个节点
        
        Args:
            **properties: 节点属性
        
        Returns:
            创建的节点实例
        """
        try:
            node = self.model_class(**properties)
            node.save()
            logger.info(f"创建{self.model_name}节点成功: uid={node.uid}")
            return node
        except Exception as e:
            logger.error(f"创建{self.model_name}节点失败: {str(e)}")
            return None
    
    def create_from_pydantic(self, pydantic_obj) -> Optional[BaseNode]:
        """
        从Pydantic模型创建节点
        
        Args:
            pydantic_obj: Pydantic模型实例
        
        Returns:
            创建的节点实例
        """
        try:
            neomodel_obj = GraphModelConverter.pydantic_to_neomodel(pydantic_obj)
            if neomodel_obj:
                neomodel_obj.save()
                logger.info(f"从Pydantic创建{self.model_name}节点成功")
                return neomodel_obj
            return None
        except Exception as e:
            logger.error(f"从Pydantic创建节点失败: {str(e)}")
            return None
    
    def bulk_create(self, items: List[Dict[str, Any]]) -> List[BaseNode]:
        """
        批量创建节点
        
        Args:
            items: 节点属性列表
        
        Returns:
            创建的节点列表
        """
        created_nodes = []
        try:
            with transaction():
                for item in items:
                    node = self.model_class(**item)
                    node.save()
                    created_nodes.append(node)
            logger.info(f"批量创建{len(created_nodes)}个{self.model_name}节点成功")
        except Exception as e:
            logger.error(f"批量创建节点失败: {str(e)}")
        return created_nodes
    
    # ==================== 查询操作 ====================
    
    def find_by_uid(self, uid: str) -> Optional[BaseNode]:
        """
        通过UID查找节点
        
        Args:
            uid: 节点唯一标识符
        
        Returns:
            节点实例或None
        """
        try:
            return self.model_class.nodes.get(uid=uid)
        except DoesNotExist:
            logger.debug(f"{self.model_name}节点不存在: uid={uid}")
            return None
        except Exception as e:
            logger.error(f"查找节点失败: {str(e)}")
            return None
    
    def find_by_property(self, **properties) -> Optional[BaseNode]:
        """
        通过属性查找单个节点
        
        Args:
            **properties: 查询属性
        
        Returns:
            第一个匹配的节点或None
        """
        try:
            return self.model_class.nodes.get(**properties)
        except DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"查找节点失败: {str(e)}")
            return None
    
    def find_all(self, **filters) -> List[BaseNode]:
        """
        查找所有匹配的节点
        
        Args:
            **filters: 过滤条件
        
        Returns:
            节点列表
        """
        try:
            if filters:
                return list(self.model_class.nodes.filter(**filters))
            else:
                return list(self.model_class.nodes.all())
        except Exception as e:
            logger.error(f"查找所有节点失败: {str(e)}")
            return []
    
    def search(self, keyword: str, properties: List[str]) -> List[BaseNode]:
        """
        搜索节点
        
        Args:
            keyword: 搜索关键词
            properties: 要搜索的属性列表
        
        Returns:
            匹配的节点列表
        """
        try:
            # 构建查询条件
            query_parts = []
            params = {}
            
            for prop in properties:
                query_parts.append(f"n.{prop} CONTAINS $keyword")
            
            where_clause = " OR ".join(query_parts) if query_parts else "true"
            
            query = f"""
                MATCH (n:{self.model_name})
                WHERE {where_clause}
                RETURN n
            """
            
            results, _ = db.cypher_query(query, {"keyword": keyword})
            
            nodes = []
            for row in results:
                node_data = row[0]
                node = self.model_class.inflate(node_data)
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            logger.error(f"搜索节点失败: {str(e)}")
            return []
    
    def paginate(self, page: int = 1, per_page: int = 10, **filters) -> Dict[str, Any]:
        """
        分页查询
        
        Args:
            page: 页码（从1开始）
            per_page: 每页数量
            **filters: 过滤条件
        
        Returns:
            包含分页信息的字典
        """
        try:
            # 获取总数
            if filters:
                query_set = self.model_class.nodes.filter(**filters)
            else:
                query_set = self.model_class.nodes.all()
            
            total = len(query_set)
            
            # 计算分页
            skip = (page - 1) * per_page
            nodes = list(query_set[skip:skip + per_page])
            
            return {
                "items": nodes,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error(f"分页查询失败: {str(e)}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "pages": 0
            }
    
    # ==================== 更新操作 ====================
    
    def update(self, uid: str, **properties) -> Optional[BaseNode]:
        """
        更新节点
        
        Args:
            uid: 节点唯一标识符
            **properties: 要更新的属性
        
        Returns:
            更新后的节点或None
        """
        try:
            node = self.find_by_uid(uid)
            if node:
                node.update_from_dict(properties)
                logger.info(f"更新{self.model_name}节点成功: uid={uid}")
                return node
            return None
        except Exception as e:
            logger.error(f"更新节点失败: {str(e)}")
            return None
    
    def update_from_pydantic(self, uid: str, pydantic_obj) -> Optional[BaseNode]:
        """
        使用Pydantic模型更新节点
        
        Args:
            uid: 节点唯一标识符
            pydantic_obj: Pydantic模型实例
        
        Returns:
            更新后的节点或None
        """
        try:
            node = self.find_by_uid(uid)
            if node:
                # 转换Pydantic到字典并更新
                data = GraphModelConverter._prepare_data_for_neomodel(
                    pydantic_obj.model_dump(exclude_none=True)
                )
                node.update_from_dict(data)
                return node
            return None
        except Exception as e:
            logger.error(f"从Pydantic更新节点失败: {str(e)}")
            return None
    
    # ==================== 删除操作 ====================
    
    def delete(self, uid: str) -> bool:
        """
        删除节点
        
        Args:
            uid: 节点唯一标识符
        
        Returns:
            是否删除成功
        """
        try:
            node = self.find_by_uid(uid)
            if node:
                node.delete()
                logger.info(f"删除{self.model_name}节点成功: uid={uid}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除节点失败: {str(e)}")
            return False
    
    def delete_all(self, **filters) -> int:
        """
        删除所有匹配的节点
        
        Args:
            **filters: 过滤条件
        
        Returns:
            删除的节点数量
        """
        try:
            nodes = self.find_all(**filters)
            count = 0
            
            with transaction():
                for node in nodes:
                    node.delete()
                    count += 1
            
            logger.info(f"删除{count}个{self.model_name}节点成功")
            return count
            
        except Exception as e:
            logger.error(f"批量删除节点失败: {str(e)}")
            return 0
    
    # ==================== 关系操作 ====================
    
    def add_relationship(
        self,
        from_uid: str,
        to_uid: str,
        relationship_type: str,
        to_model_class: Type[BaseNode],
        **rel_properties
    ) -> bool:
        """
        添加关系
        
        Args:
            from_uid: 起始节点UID
            to_uid: 目标节点UID
            relationship_type: 关系类型
            to_model_class: 目标节点模型类
            **rel_properties: 关系属性
        
        Returns:
            是否成功
        """
        try:
            from_node = self.find_by_uid(from_uid)
            to_node = to_model_class.nodes.get(uid=to_uid)
            
            if from_node and to_node:
                # 获取关系定义
                rel_def = getattr(from_node, relationship_type.lower(), None)
                if rel_def:
                    rel_def.connect(to_node, rel_properties)
                    logger.info(f"添加关系成功: {from_uid}-[{relationship_type}]->{to_uid}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"添加关系失败: {str(e)}")
            return False
    
    def get_relationships(
        self,
        uid: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取节点的关系
        
        Args:
            uid: 节点UID
            relationship_type: 关系类型（可选）
        
        Returns:
            关系列表
        """
        try:
            node = self.find_by_uid(uid)
            if not node:
                return []
            
            relationships = []
            
            if relationship_type:
                # 获取特定类型的关系
                rel_def = getattr(node, relationship_type.lower(), None)
                if rel_def:
                    for related_node in rel_def.all():
                        relationships.append({
                            "type": relationship_type,
                            "node": related_node.to_dict()
                        })
            else:
                # 获取所有关系
                for attr_name in dir(node):
                    attr = getattr(node, attr_name)
                    if hasattr(attr, 'all'):
                        try:
                            related_nodes = attr.all()
                            for related_node in related_nodes:
                                relationships.append({
                                    "type": attr_name.upper(),
                                    "node": related_node.to_dict()
                                })
                        except:
                            pass
            
            return relationships
            
        except Exception as e:
            logger.error(f"获取关系失败: {str(e)}")
            return []