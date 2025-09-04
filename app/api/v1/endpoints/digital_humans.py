from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.schemas.digital_human import (
    DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanResponse, 
    DigitalHumanPageRequest, DigitalHumanPageResponse, DigitalHumanDetailRequest, 
    DigitalHumanUpdateRequest, DigitalHumanDeleteRequest, DigitalHumanTrainRequest
)
from app.schemas.common_response import SuccessResponse
from app.schemas.common_response import PaginationMeta
from typing import Optional
import math
import json
import asyncio
from app.core.logger import logger
from app.services.digital_human_service import DigitalHumanService
from app.services.digital_human_training_service import DigitalHumanTrainingService
from app.dependencies.services import get_digital_human_training_service
from app.core.database import get_db
from app.core.models import User
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil

router = APIRouter()


def get_digital_human_service(db: Session = Depends(get_db)) -> DigitalHumanService:
    return DigitalHumanService(db)


@router.post("/create", response_model=SuccessResponse[DigitalHumanResponse], summary="创建数字人模板")
async def create_digital_human_template(
    digital_human_data: DigitalHumanCreate,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service)
):
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
    logger.info(f"📋 用户 {current_user.id} 获取数字人列表 - 页码: {request.page}, 每页: {request.size}, 包含公开: {request.include_public}")
    
    digital_humans, total = digital_human_service.get_digital_humans_paginated(
        request, current_user.id, request.include_public
    )
    
    logger.debug(f"📊 查询到 {len(digital_humans)} 个数字人模板，总计 {total} 个")
    
    total_pages = math.ceil(total / request.size)
    
    pagination = PaginationMeta(
        page=request.page,
        size=request.size,
        total=total,
        pages=total_pages
    )
    
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
    logger.info(f"📝 用户 {current_user.id} 更新数字人: ID={request.id}")
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
    logger.info(f"🗑️ 用户 {current_user.id} 删除数字人: ID={request.id}")
    digital_human_service.delete_digital_human(request.id, current_user.id)
    logger.success(f"✅ 数字人删除成功: ID={request.id}")
    return ResponseUtil.success(message="数字人模板删除成功")


@router.post("/train", summary="训练数字人")
async def train_digital_human(
    request: DigitalHumanTrainRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    training_service: DigitalHumanTrainingService = Depends(get_digital_human_training_service)
):
    digital_human = digital_human_service.get_digital_human_by_id(
        request.digital_human_id, 
        current_user.id
    )
    
    if not digital_human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数字人不存在或您无权限训练"
        )
    
    logger.info(f"🎓 用户 {current_user.id} 开始训练数字人: ID={request.digital_human_id}, 消息={request.message[:50]}...")
    
    async def generate():
        try:
            async for chunk in training_service.process_training_conversation(
                request.digital_human_id,
                request.message,
                current_user.id
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.error(f"训练流生成失败: {str(e)}")
            error_msg = json.dumps({
                "type": "error",
                "data": "训练过程出现错误，请重试"
            }, ensure_ascii=False)
            yield f"data: {error_msg}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )