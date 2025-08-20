from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.digital_human import DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanResponse, DigitalHumanPageRequest, DigitalHumanPageResponse, DigitalHumanDetailRequest, DigitalHumanUpdateRequest, DigitalHumanDeleteRequest
from app.schemas.common_response import SuccessResponse
from app.schemas.common_response import PaginationMeta
from typing import Optional
import math
from app.core.logger import logger  # 使用 loguru logger
from app.services.digital_human_service import DigitalHumanService
from app.core.database import get_db
from app.core.models import User
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil

router = APIRouter()


def get_digital_human_service(db: Session = Depends(get_db)) -> DigitalHumanService:
    """获取数字人服务实例"""
    return DigitalHumanService(db)


@router.post("/create", response_model=SuccessResponse[DigitalHumanResponse], summary="创建数字人模板")
async def create_digital_human_template(
    digital_human_data: DigitalHumanCreate,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    创建数字人模板
    
    - **name**: 数字人名称（必填）
    - **short_description**: 简短描述
    - **detailed_description**: 详细介绍
    - **type**: 数字人类型（默认"专业助手"）
    - **skills**: 专业领域技能列表
    - **personality**: 性格特征配置
    - **conversation_style**: 对话风格（默认"专业严谨"）
    - **temperature**: AI温度参数（0-2，默认0.7）
    - **max_tokens**: 最大token数（1-8192，默认2048）
    - **system_prompt**: 系统提示词
    - **is_public**: 是否公开模板
    """
    logger.info(f"👤 用户 {current_user.id} 创建数字人模板: {digital_human_data.name}")
    digital_human = digital_human_service.create_digital_human(digital_human_data, current_user.id)
    logger.success(f"✅ 数字人模板创建成功: ID={digital_human.id}, 名称={digital_human.name}")
    return ResponseUtil.success(data=digital_human, message="数字人模板创建成功")


@router.post("/page", response_model=DigitalHumanPageResponse, summary="分页获取数字人模板列表")
async def get_digital_human_templates(
    request: DigitalHumanPageRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    分页获取数字人模板列表
    
    - **page**: 页码,从1开始(默认1)
    - **size**: 每页数量,最大100(默认10)
    - **search**: 搜索关键词,搜索名称和描述(可选)
    - **include_public**: 是否包含公开模板(默认true)
    
    返回数据包含分页信息和数字人模板列表
    """
    logger.info(f"📋 用户 {current_user.id} 获取数字人列表 - 页码: {request.page}, 每页: {request.size}, 包含公开: {request.include_public}")
    
    # 获取分页数据
    digital_humans, total = digital_human_service.get_digital_humans_paginated(
        request, current_user.id, request.include_public
    )
    
    logger.debug(f"📊 查询到 {len(digital_humans)} 个数字人模板，总计 {total} 个")
    
    # 计算总页数
    total_pages = math.ceil(total / request.size)
    
    # 构建分页元数据
    pagination = PaginationMeta(
        page=request.page,
        size=request.size,
        total=total,
        pages=total_pages
    )
    
    # 转换为响应模型
    digital_human_responses = [DigitalHumanResponse.from_orm(dh) for dh in digital_humans]
    
    logger.info(f"✔️ 成功返回 {len(digital_human_responses)} 个数字人模板给用户 {current_user.id}")
    
    return DigitalHumanPageResponse(
        code=200,
        message="获取数字人模板列表成功",
        data=digital_human_responses,
        pagination=pagination
    )


@router.post("/detail", response_model=SuccessResponse[DigitalHumanResponse], summary="获取数字人模板详情")
async def get_digital_human_template(
    request: DigitalHumanDetailRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    根据ID获取数字人模板详情
    
    - **id**: 数字人模板ID
    """
    logger.info(f"🔍 用户 {current_user.id} 获取数字人详情: ID={request.id}")
    digital_human = digital_human_service.get_digital_human_by_id(request.id, current_user.id)
    logger.success(f"✅ 成功获取数字人详情: ID={request.id}, 名称={digital_human.name}")
    return ResponseUtil.success(data=digital_human, message="获取数字人模板详情成功")


@router.post("/update", response_model=SuccessResponse[DigitalHumanResponse], summary="更新数字人模板")
async def update_digital_human_template(
    request: DigitalHumanUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    更新数字人模板信息
    
    - **id**: 数字人模板ID
    - 其他字段均为可选，只更新提供的字段
    """
    logger.info(f"📝 用户 {current_user.id} 更新数字人: ID={request.id}")
    # 将DigitalHumanUpdateRequest转换为DigitalHumanUpdate（不包含id）
    update_data = DigitalHumanUpdate(**request.model_dump(exclude={'id'}))
    digital_human = digital_human_service.update_digital_human(request.id, update_data, current_user.id)
    logger.success(f"✅ 数字人更新成功: ID={request.id}, 名称={digital_human.name}")
    return ResponseUtil.success(data=digital_human, message="数字人模板更新成功")


@router.post("/delete", response_model=SuccessResponse[None], summary="删除数字人模板")
async def delete_digital_human_template(
    request: DigitalHumanDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
    """
    删除数字人模板
    
    - **id**: 数字人模板ID
    """
    logger.info(f"🗑️ 用户 {current_user.id} 删除数字人: ID={request.id}")
    digital_human_service.delete_digital_human(request.id, current_user.id)
    logger.success(f"✅ 数字人删除成功: ID={request.id}")
    return ResponseUtil.success(message="数字人模板删除成功")
