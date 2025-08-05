from typing import Any, Optional, List
from app.schemas.common import BaseResponse, SuccessResponse, ErrorResponse
import math


class ResponseUtil:
    """响应工具类"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        code: int = 200
    ) -> SuccessResponse:
        """构造成功响应"""
        return SuccessResponse(
            code=code,
            message=message,
            data=data
        )
    
    @staticmethod
    def error(
        message: str = "操作失败",
        code: int = 400
    ) -> ErrorResponse:
        """构造错误响应"""
        return ErrorResponse(
            code=code,
            message=message
        )
    
    @staticmethod
    def page_success(
        data: List[Any],
        page: int,
        size: int,
        total: int,
        message: str = "查询成功"
    ) -> dict:
        """构造分页成功响应"""
        total_pages = math.ceil(total / size) if size > 0 else 0
        return {
            "code": 200,
            "message": message,
            "data": data,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": total_pages
            }
        }
    
    @staticmethod
    def unauthorized(message: str = "未授权访问") -> ErrorResponse:
        """构造未授权响应"""
        return ResponseUtil.error(message=message, code=401)
    
    @staticmethod
    def forbidden(message: str = "权限不足") -> ErrorResponse:
        """构造禁止访问响应"""
        return ResponseUtil.error(message=message, code=403)
    
    @staticmethod
    def not_found(message: str = "资源不存在") -> ErrorResponse:
        """构造资源不存在响应"""
        return ResponseUtil.error(message=message, code=404)
    
    @staticmethod
    def internal_error(message: str = "服务器内部错误") -> ErrorResponse:
        """构造服务器错误响应"""
        return ResponseUtil.error(message=message, code=500) 