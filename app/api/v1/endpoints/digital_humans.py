from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.digital_human import DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanResponse, DigitalHumanPageRequest, DigitalHumanPageResponse
from app.schemas.common import SuccessResponse
from app.schemas.CommonResponse import PaginationMeta
from typing import Optional
import math
from app.services.digital_human_service import DigitalHumanService
from app.core.database import get_db
from app.core.models import User
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil

router = APIRouter()


def get_digital_human_service(db: Session = Depends(get_db)) -> DigitalHumanService:
    """获取数字人服务实例"""
    return DigitalHumanService(db)


@router.post("/", response_model=SuccessResponse[DigitalHumanResponse], summary="创建数字人")
async def create_digital_human(
    digital_human_data: DigitalHumanCreate,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    创建数字人
    
    - **name**: 数字人名称（必填）
    - **short_description**: 简短描述
    - **detailed_description**: 详细介绍
    - **type**: 数字人类型（默认"专业助手"）
    - **skills**: 专业领域技能列表
    - **personality**: 性格特征配置
    - **conversation_style**: 对话风格（默认"专业严谨"）
    - **temperature**: AI温度参数（0-2，默认0.7）
    - **max_tokens**: 最大token数（1-8192，默认2048）
    """
    digital_human = digital_human_service.create_digital_human(digital_human_data, current_user.id)
    return ResponseUtil.success(data=digital_human, message="数字人创建成功")


@router.get("/page", response_model=DigitalHumanPageResponse, summary="分页获取数字人列表")
async def get_digital_humans_page(
    page: int = 1,
    size: int = 10,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    分页获取数字人列表
    
    - **page**: 页码,从1开始(默认1)
    - **size**: 每页数量,最大100(默认10)
    - **search**: 搜索关键词,搜索名称和描述(可选)
    
    返回数据包含分页信息和数字人列表
    """
    # 构建分页请求对象
    page_request = DigitalHumanPageRequest(
        page=page,
        size=size,
        search=search
    )
    
    # 获取分页数据
    digital_humans, total = digital_human_service.get_digital_humans_paginated(page_request, current_user.id)
    
    # 计算总页数
    total_pages = math.ceil(total / size)
    
    # 构建分页元数据
    pagination = PaginationMeta(
        page=page,
        size=size,
        total=total,
        pages=total_pages
    )
    
    # 转换为响应模型
    digital_human_responses = [DigitalHumanResponse.from_orm(dh) for dh in digital_humans]
    
    return DigitalHumanPageResponse(
        code=200,
        message="获取数字人列表成功",
        data=digital_human_responses,
        pagination=pagination
    )


@router.get("/{digital_human_id}", response_model=SuccessResponse[DigitalHumanResponse], summary="获取数字人详情")
async def get_digital_human(
    digital_human_id: int,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    根据ID获取数字人详情
    
    - **digital_human_id**: 数字人ID
    """
    digital_human = digital_human_service.get_digital_human_by_id(digital_human_id, current_user.id)
    return ResponseUtil.success(data=digital_human, message="获取数字人详情成功")


@router.put("/{digital_human_id}", response_model=SuccessResponse[DigitalHumanResponse], summary="更新数字人")
async def update_digital_human(
    digital_human_id: int,
    digital_human_data: DigitalHumanUpdate,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    更新数字人信息
    
    - **digital_human_id**: 数字人ID
    - 其他字段均为可选，只更新提供的字段
    """
    digital_human = digital_human_service.update_digital_human(digital_human_id, digital_human_data, current_user.id)
    return ResponseUtil.success(data=digital_human, message="数字人更新成功")


@router.delete("/{digital_human_id}", response_model=SuccessResponse[None], summary="删除数字人")
async def delete_digital_human(
    digital_human_id: int,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    删除数字人
    
    - **digital_human_id**: 数字人ID
    """
    digital_human_service.delete_digital_human(digital_human_id, current_user.id)
    return ResponseUtil.success(message="数字人删除成功")
