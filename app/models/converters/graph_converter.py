"""
图模型转换器
实现Pydantic模型和Neomodel模型之间的双向转换
"""

from typing import Any, Dict, Type, Optional
from datetime import datetime, date
import logging

from app.models.graph.nodes.person import PersonNode
from app.models.graph.nodes.organization import OrganizationNode
# TODO: 以下模型尚未实现
# from app.models.graph.nodes.location import LocationNode
# from app.models.graph.nodes.event import EventNode
# from app.models.graph.nodes.project import ProjectNode
# from app.models.graph.nodes.product import ProductNode

from app.models.neomodel.nodes import (
    Person,
    Organization,
    Location,
    Event,
    Project,
    Product,
    Tag,
    Category
)

logger = logging.getLogger(__name__)


class GraphModelConverter:
    """
    图模型转换器
    负责Pydantic模型和Neomodel模型之间的转换
    """
    
    # 模型映射关系
    PYDANTIC_TO_NEOMODEL = {
        PersonNode: Person,
        OrganizationNode: Organization,
        # TODO: 添加其他模型映射
        # LocationNode: Location,
        # EventNode: Event,
        # ProjectNode: Project,
        # ProductNode: Product,
    }
    
    NEOMODEL_TO_PYDANTIC = {v: k for k, v in PYDANTIC_TO_NEOMODEL.items()}
    
    @classmethod
    def pydantic_to_neomodel(cls, pydantic_obj: Any) -> Optional[Any]:
        """
        将Pydantic模型实例转换为Neomodel模型实例
        
        Args:
            pydantic_obj: Pydantic模型实例
            
        Returns:
            Neomodel模型实例，如果转换失败返回None
        """
        try:
            # 获取对应的Neomodel类
            pydantic_class = type(pydantic_obj)
            neomodel_class = cls.PYDANTIC_TO_NEOMODEL.get(pydantic_class)
            
            if not neomodel_class:
                logger.warning(f"未找到Pydantic类 {pydantic_class.__name__} 的Neomodel映射")
                return None
            
            # 转换数据
            data = cls._prepare_data_for_neomodel(pydantic_obj.model_dump(exclude_none=True))
            
            # 创建Neomodel实例
            neomodel_obj = neomodel_class(**data)
            
            return neomodel_obj
            
        except Exception as e:
            logger.error(f"Pydantic转Neomodel失败: {str(e)}")
            return None
    
    @classmethod
    def neomodel_to_pydantic(cls, neomodel_obj: Any) -> Optional[Any]:
        """
        将Neomodel模型实例转换为Pydantic模型实例
        
        Args:
            neomodel_obj: Neomodel模型实例
            
        Returns:
            Pydantic模型实例，如果转换失败返回None
        """
        try:
            # 获取对应的Pydantic类
            neomodel_class = type(neomodel_obj)
            pydantic_class = cls.NEOMODEL_TO_PYDANTIC.get(neomodel_class)
            
            if not pydantic_class:
                logger.warning(f"未找到Neomodel类 {neomodel_class.__name__} 的Pydantic映射")
                return None
            
            # 转换数据
            data = cls._prepare_data_for_pydantic(neomodel_obj.to_dict())
            
            # 创建Pydantic实例
            pydantic_obj = pydantic_class(**data)
            
            return pydantic_obj
            
        except Exception as e:
            logger.error(f"Neomodel转Pydantic失败: {str(e)}")
            return None
    
    @classmethod
    def _prepare_data_for_neomodel(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备用于Neomodel的数据
        
        Args:
            data: 原始数据字典
            
        Returns:
            处理后的数据字典
        """
        result = {}
        
        for key, value in data.items():
            # 跳过Pydantic特有的字段
            if key in ['id', 'labels']:
                continue
            
            # 处理日期时间类型
            if isinstance(value, datetime):
                result[key] = value
            elif isinstance(value, date):
                result[key] = value
            elif isinstance(value, dict):
                # JSON字段直接传递
                result[key] = value
            elif isinstance(value, list):
                # 数组字段直接传递
                result[key] = value
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def _prepare_data_for_pydantic(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备用于Pydantic的数据
        
        Args:
            data: 原始数据字典
            
        Returns:
            处理后的数据字典
        """
        result = {}
        
        for key, value in data.items():
            # 跳过Neomodel特有的字段
            if key in ['uid']:
                if key == 'uid':
                    result['id'] = value  # uid映射到id
                continue
            
            # 处理日期时间字符串
            if isinstance(value, str) and key.endswith('_at'):
                try:
                    result[key] = datetime.fromisoformat(value)
                except:
                    result[key] = value
            elif isinstance(value, str) and key.endswith('_date'):
                try:
                    result[key] = date.fromisoformat(value)
                except:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def bulk_convert_to_neomodel(cls, pydantic_objects: list) -> list:
        """
        批量转换Pydantic模型到Neomodel
        
        Args:
            pydantic_objects: Pydantic模型实例列表
            
        Returns:
            Neomodel模型实例列表
        """
        results = []
        for obj in pydantic_objects:
            converted = cls.pydantic_to_neomodel(obj)
            if converted:
                results.append(converted)
        return results
    
    @classmethod
    def bulk_convert_to_pydantic(cls, neomodel_objects: list) -> list:
        """
        批量转换Neomodel模型到Pydantic
        
        Args:
            neomodel_objects: Neomodel模型实例列表
            
        Returns:
            Pydantic模型实例列表
        """
        results = []
        for obj in neomodel_objects:
            converted = cls.neomodel_to_pydantic(obj)
            if converted:
                results.append(converted)
        return results