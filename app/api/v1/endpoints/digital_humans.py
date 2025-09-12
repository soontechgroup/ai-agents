from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.schemas.digital_human import (
    DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanResponse, 
    DigitalHumanPageRequest, DigitalHumanPageResponse, DigitalHumanDetailRequest, 
    DigitalHumanUpdateRequest, DigitalHumanDeleteRequest, DigitalHumanTrainRequest,
    MemoryGraphRequest, MemoryGraphResponse, MemoryGraphNode, MemoryGraphEdge, MemoryGraphStatistics,
    TrainingMessagesRequest, TrainingMessageResponse, TrainingMessagesPageResponse,
    TrainingSessionResponse, TrainingSessionListRequest, TrainingSessionPageResponse,
    CompleteTrainingSessionRequest, TrainingSessionSummary
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
from app.services.graph_service import GraphService
from app.dependencies.services import get_digital_human_training_service, get_training_session_repository
from app.repositories.training_session_repository import TrainingSessionRepository
from app.core.database import get_db
from app.core.models import User
from app.guards import get_current_active_user
from app.utils.response import ResponseUtil

router = APIRouter()


def get_digital_human_service(db: Session = Depends(get_db)) -> DigitalHumanService:
    return DigitalHumanService(db)


def get_graph_service() -> GraphService:
    return GraphService()


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


@router.post("/memory-graph", response_model=SuccessResponse[MemoryGraphResponse], summary="获取数字人记忆图谱")
async def get_digital_human_memory_graph(
    request: MemoryGraphRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    graph_service: GraphService = Depends(get_graph_service)
):
    """
    获取指定数字人的记忆图谱数据，用于前端可视化展示
    
    权限验证：
    - 用户只能查看自己创建的数字人记忆
    - 公开的数字人记忆暂不支持查看
    
    返回格式：
    - nodes: 知识节点列表，包含节点ID、标签、类型、大小等信息
    - edges: 关系边列表，包含源节点、目标节点、关系类型等信息
    - statistics: 统计信息，包含总节点数、总边数、各类型节点数量等
    """
    # 验证用户是否有权限访问该数字人
    digital_human = digital_human_service.get_digital_human_by_id(
        request.digital_human_id, 
        current_user.id
    )
    
    if not digital_human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数字人不存在或您无权限访问"
        )
    
    logger.info(f"📊 用户 {current_user.id} 获取数字人记忆图谱: ID={request.digital_human_id}")
    
    # 获取记忆图谱数据
    graph_data = await graph_service.get_digital_human_memory_graph(
        digital_human_id=request.digital_human_id,
        limit=request.limit,
        node_types=request.node_types
    )
    
    # 检查是否有错误
    if "error" in graph_data:
        logger.error(f"获取记忆图谱失败: {graph_data['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取记忆图谱失败，请稍后重试"
        )
    
    # 构建响应
    memory_graph = MemoryGraphResponse(
        nodes=[MemoryGraphNode(**node) for node in graph_data["nodes"]],
        edges=[MemoryGraphEdge(**edge) for edge in graph_data["edges"]],
        statistics=MemoryGraphStatistics(**graph_data["statistics"])
    )
    
    logger.success(f"✅ 成功获取数字人记忆图谱: {graph_data['statistics']['displayed_nodes']} 个节点, {graph_data['statistics']['displayed_edges']} 条边")
    
    return ResponseUtil.success(data=memory_graph, message="获取数字人记忆图谱成功")


@router.post("/training-messages", response_model=TrainingMessagesPageResponse, summary="获取数字人训练消息历史")
async def get_training_messages(
    request: TrainingMessagesRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    training_service: DigitalHumanTrainingService = Depends(get_digital_human_training_service)
):
    """
    获取数字人训练消息历史
    
    权限验证：
    - 用户只能查看自己创建的数字人的训练消息
    
    返回格式：
    - 分页的训练消息列表
    - 包含用户消息和助手回复
    - 包含抽取的知识（如果有）
    """
    # 验证用户权限
    digital_human = digital_human_service.get_digital_human_by_id(
        request.digital_human_id, 
        current_user.id
    )
    
    if not digital_human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数字人不存在或您无权限访问"
        )
    
    logger.info(f"📜 用户 {current_user.id} 获取数字人训练消息: ID={request.digital_human_id}, 页码={request.page}, 每页={request.size}")
    
    # 获取训练消息历史
    messages, total = training_service.get_training_history(
        digital_human_id=request.digital_human_id,
        page=request.page,
        size=request.size
    )
    
    # 构建分页信息
    total_pages = math.ceil(total / request.size)
    pagination = PaginationMeta(
        page=request.page,
        size=request.size,
        total=total,
        pages=total_pages
    )
    
    # 构建响应
    message_responses = [TrainingMessageResponse.from_orm(msg) for msg in messages]
    
    logger.success(f"✅ 成功获取训练消息: 返回 {len(message_responses)} 条消息，总计 {total} 条")
    
    return TrainingMessagesPageResponse(
        code=200,
        message="获取训练消息历史成功",
        data=message_responses,
        pagination=pagination
    )


@router.post("/training-sessions", response_model=TrainingSessionPageResponse, summary="获取训练会话列表")
async def get_training_sessions(
    request: TrainingSessionListRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    session_repo: TrainingSessionRepository = Depends(get_training_session_repository)
):
    """
    获取用户的训练会话列表
    
    权限验证：
    - 用户只能查看自己的训练会话
    - 如果指定了 digital_human_id，验证用户是否有权限访问该数字人
    """
    # 如果指定了数字人ID，验证权限
    if request.digital_human_id:
        digital_human = digital_human_service.get_digital_human_by_id(
            request.digital_human_id, 
            current_user.id
        )
        
        if not digital_human:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数字人不存在或您无权限访问"
            )
    
    logger.info(f"📚 用户 {current_user.id} 获取训练会话列表: 数字人={request.digital_human_id}, 状态={request.status}")
    
    # 获取会话列表
    offset = (request.page - 1) * request.size
    sessions, total = session_repo.get_user_sessions(
        user_id=current_user.id,
        digital_human_id=request.digital_human_id,
        status=request.status,
        limit=request.size,
        offset=offset
    )
    
    # 构建分页信息
    total_pages = math.ceil(total / request.size)
    pagination = PaginationMeta(
        page=request.page,
        size=request.size,
        total=total,
        pages=total_pages
    )
    
    # 构建响应
    session_responses = [TrainingSessionResponse.from_orm(session) for session in sessions]
    
    logger.success(f"✅ 成功获取训练会话: 返回 {len(session_responses)} 个会话，总计 {total} 个")
    
    return TrainingSessionPageResponse(
        code=200,
        message="获取训练会话列表成功",
        data=session_responses,
        pagination=pagination
    )


@router.post("/training-session/complete", response_model=SuccessResponse[TrainingSessionResponse], summary="完成训练会话")
async def complete_training_session(
    request: CompleteTrainingSessionRequest,
    current_user: User = Depends(get_current_active_user),
    session_repo: TrainingSessionRepository = Depends(get_training_session_repository),
    graph_service: GraphService = Depends(get_graph_service)
):
    """
    完成训练会话并生成知识总结
    
    权限验证：
    - 用户只能完成自己的训练会话
    - 会话必须处于进行中状态
    """
    # 获取会话并验证权限
    session = session_repo.get_session_by_id(request.session_id, current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="训练会话不存在或您无权限访问"
        )
    
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"会话状态不正确，当前状态: {session.status}"
        )
    
    logger.info(f"🏁 用户 {current_user.id} 完成训练会话: ID={request.session_id}, 应用知识={request.apply_knowledge}")
    
    # 获取会话统计
    messages = session_repo.get_session_messages(request.session_id)
    entities_count = 0
    relations_count = 0
    
    for msg in messages:
        if msg.extracted_knowledge:
            entities_count += len(msg.extracted_knowledge.get('entities', []))
            relations_count += len(msg.extracted_knowledge.get('relationships', []))
    
    # 生成知识总结
    knowledge_summary = {
        "total_messages": len(messages),
        "entities_extracted": entities_count,
        "relations_extracted": relations_count,
        "completion_time": datetime.now().isoformat()
    }
    
    # 更新会话状态
    status = "applied" if request.apply_knowledge else "completed"
    updated_session = session_repo.complete_session_with_summary(
        session_id=request.session_id,
        entities_count=entities_count,
        relations_count=relations_count,
        knowledge_summary=knowledge_summary
    )
    
    if request.apply_knowledge:
        updated_session = session_repo.update_session_status(
            session_id=request.session_id,
            status="applied"
        )
    
    logger.success(f"✅ 训练会话完成: ID={request.session_id}, 实体={entities_count}, 关系={relations_count}")
    
    return ResponseUtil.success(
        data=TrainingSessionResponse.from_orm(updated_session),
        message="训练会话已完成"
    )


@router.get("/training-sessions/summary", response_model=SuccessResponse[TrainingSessionSummary], summary="获取训练会话摘要")
async def get_training_sessions_summary(
    digital_human_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session_repo: TrainingSessionRepository = Depends(get_training_session_repository)
):
    """
    获取用户的训练会话摘要统计
    
    权限验证：
    - 用户只能查看自己的训练会话统计
    """
    logger.info(f"📊 用户 {current_user.id} 获取训练会话摘要: 数字人={digital_human_id}")
    
    # 获取活跃会话
    active_sessions, _ = session_repo.get_user_sessions(
        user_id=current_user.id,
        digital_human_id=digital_human_id,
        status="in_progress",
        limit=1000,
        offset=0
    )
    
    # 获取已完成会话
    completed_sessions, _ = session_repo.get_user_sessions(
        user_id=current_user.id,
        digital_human_id=digital_human_id,
        status="completed",
        limit=1000,
        offset=0
    )
    
    # 统计总实体和关系数
    total_entities = 0
    total_relations = 0
    
    for session in completed_sessions:
        total_entities += session.extracted_entities or 0
        total_relations += session.extracted_relations or 0
    
    summary = TrainingSessionSummary(
        active_sessions=len(active_sessions),
        completed_sessions=len(completed_sessions),
        total_entities=total_entities,
        total_relations=total_relations
    )
    
    logger.success(f"✅ 获取训练会话摘要成功: 活跃={len(active_sessions)}, 完成={len(completed_sessions)}")
    
    return ResponseUtil.success(data=summary, message="获取训练会话摘要成功")