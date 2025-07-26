from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.digital_human import DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanResponse
from app.schemas.common import SuccessResponse
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


@router.get("/", response_model=SuccessResponse[List[DigitalHumanResponse]], summary="获取用户数字人列表")
async def get_user_digital_humans(
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    获取当前用户的所有数字人
    
    返回按创建时间倒序排列的数字人列表
    """
    digital_humans = digital_human_service.get_user_digital_humans(current_user.id)
    return ResponseUtil.success(data=digital_humans, message="获取数字人列表成功")


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