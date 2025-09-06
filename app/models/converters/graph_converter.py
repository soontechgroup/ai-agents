"""
图模型转换器
实现Pydantic模型和Neomodel模型之间的双向转换
"""

import logging
from datetime import datetime, date
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GraphModelConverter:
    
    PYDANTIC_TO_NEOMODEL = {}
    
    NEOMODEL_TO_PYDANTIC = {}
    
    @classmethod
    def pydantic_to_neomodel(cls, pydantic_obj: Any) -> Optional[Any]:
        try:
            pydantic_class = type(pydantic_obj)
            neomodel_class = cls.PYDANTIC_TO_NEOMODEL.get(pydantic_class)
            
            if not neomodel_class:
                logger.warning(f"未找到Pydantic类 {pydantic_class.__name__} 的Neomodel映射")
                return None
            
            data = cls._prepare_data_for_neomodel(pydantic_obj.model_dump(exclude_none=True))
            neomodel_obj = neomodel_class(**data)
            
            return neomodel_obj
            
        except Exception as e:
            logger.error(f"Pydantic转Neomodel失败: {str(e)}")
            return None
    
    @classmethod
    def neomodel_to_pydantic(cls, neomodel_obj: Any) -> Optional[Any]:
        try:
            neomodel_class = type(neomodel_obj)
            pydantic_class = cls.NEOMODEL_TO_PYDANTIC.get(neomodel_class)
            
            if not pydantic_class:
                logger.warning(f"未找到Neomodel类 {neomodel_class.__name__} 的Pydantic映射")
                return None
            
            data = cls._prepare_data_for_pydantic(neomodel_obj.to_dict())
            pydantic_obj = pydantic_class(**data)
            
            return pydantic_obj
            
        except Exception as e:
            logger.error(f"Neomodel转Pydantic失败: {str(e)}")
            return None
    
    @classmethod
    def _prepare_data_for_neomodel(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        
        for key, value in data.items():
            if key in ['id', 'labels']:
                continue
            if key == 'uid' and value is None:
                continue
            
            if isinstance(value, datetime):
                result[key] = value
            elif isinstance(value, date):
                result[key] = value
            elif isinstance(value, dict):
                result[key] = value
            elif isinstance(value, list):
                result[key] = value
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def _prepare_data_for_pydantic(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        
        for key, value in data.items():
            if key == 'uid':
                result['uid'] = value
                result['id'] = value
                continue
            
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
        results = []
        for obj in pydantic_objects:
            converted = cls.pydantic_to_neomodel(obj)
            if converted:
                results.append(converted)
        return results
    
    @classmethod
    def bulk_convert_to_pydantic(cls, neomodel_objects: list) -> list:
        results = []
        for obj in neomodel_objects:
            converted = cls.neomodel_to_pydantic(obj)
            if converted:
                results.append(converted)
        return results