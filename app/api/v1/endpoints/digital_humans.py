from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.schemas.digital_human import (
    DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanResponse, 
    DigitalHumanPageRequest, DigitalHumanPageResponse, DigitalHumanDetailRequest, 
    DigitalHumanUpdateRequest, DigitalHumanDeleteRequest, DigitalHumanTrainRequest,
    MemoryGraphRequest, MemoryGraphResponse, MemoryGraphNode, MemoryGraphEdge, MemoryGraphStatistics,
    TrainingMessagesRequest, TrainingMessageResponse, TrainingMessagesPageResponse,
    MemorySearchRequest, MemoryDetailRequest, MemoryDetailResponse,
    MemoryStatsRequest, MemoryStatsResponse
)
from app.schemas.common_response import SuccessResponse
from app.schemas.common_response import PaginationMeta
from typing import Optional, List
import math
import json
import asyncio
from app.core.logger import logger
from app.services.digital_human_service import DigitalHumanService
from app.services.digital_human_training_service import DigitalHumanTrainingService
from app.services.graph_service import GraphService
from app.dependencies.services import get_digital_human_training_service
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
    
    digital_human_responses = [DigitalHumanResponse.model_validate(dh) for dh in digital_humans]
    
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
    message_responses = [TrainingMessageResponse.model_validate(msg) for msg in messages]
    
    logger.success(f"✅ 成功获取训练消息: 返回 {len(message_responses)} 条消息，总计 {total} 条")
    
    return TrainingMessagesPageResponse(
        code=200,
        message="获取训练消息历史成功",
        data=message_responses,
        pagination=pagination
    )


@router.post("/memory-search", response_model=SuccessResponse[List[MemoryGraphNode]], summary="搜索数字人记忆")
async def search_memory(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    graph_service: GraphService = Depends(get_graph_service)
):
    """搜索数字人的记忆节点"""
    digital_human = digital_human_service.get_digital_human_by_id(
        request.digital_human_id, 
        current_user.id
    )
    
    if not digital_human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数字人不存在或您无权限访问"
        )
    
    logger.info(f"🔍 用户 {current_user.id} 搜索数字人记忆: ID={request.digital_human_id}, 关键词={request.query}")
    
    search_result = await graph_service.search_digital_human_memories(
        digital_human_id=request.digital_human_id,
        query=request.query,
        node_types=request.node_types,
        limit=request.limit
    )
    
    if not search_result.get("success", False):
        logger.error(f"搜索记忆失败: {search_result.get('error')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索记忆失败，请稍后重试"
        )
    
    memory_nodes = [
        MemoryGraphNode(
            id=node["id"],
            label=node["label"],
            type=node["type"],
            size=10 + node.get("confidence", 0.5) * 20,
            confidence=node.get("confidence", 0.5),
            properties=node.get("properties", {}),
            updated_at=node.get("updated_at")
        )
        for node in search_result.get("results", [])
    ]
    
    logger.success(f"✅ 搜索完成: 找到 {len(memory_nodes)} 个匹配的记忆节点")
    
    return ResponseUtil.success(data=memory_nodes, message=f"搜索到 {len(memory_nodes)} 个记忆节点")


@router.post("/memory-detail", response_model=SuccessResponse[MemoryDetailResponse], summary="获取记忆节点详情")
async def get_memory_detail(
    request: MemoryDetailRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    graph_service: GraphService = Depends(get_graph_service)
):
    """获取特定记忆节点的详细信息"""
    digital_human = digital_human_service.get_digital_human_by_id(
        request.digital_human_id, 
        current_user.id
    )
    
    if not digital_human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数字人不存在或您无权限访问"
        )
    
    logger.info(f"📝 用户 {current_user.id} 获取记忆节点详情: 数字人ID={request.digital_human_id}, 节点ID={request.node_id}")
    
    detail_result = await graph_service.get_memory_node_detail(
        digital_human_id=request.digital_human_id,
        node_id=request.node_id,
        include_relations=request.include_relations,
        relation_depth=request.relation_depth
    )
    
    if not detail_result.get("success", False):
        error_msg = detail_result.get("error", "未知错误")
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="记忆节点不存在"
            )
        else:
            logger.error(f"获取记忆节点详情失败: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取记忆节点详情失败"
            )
    
    node_data = detail_result.get("node", {})
    memory_node = MemoryGraphNode(
        id=node_data.get("id", ""),
        label=node_data.get("label", ""),
        type=node_data.get("type", "unknown"),
        size=10 + node_data.get("confidence", 0.5) * 20,
        confidence=node_data.get("confidence", 0.5),
        properties=node_data.get("properties", {}),
        updated_at=node_data.get("updated_at")
    )
    
    connected_nodes = [
        MemoryGraphNode(
            id=node["id"],
            label=node["label"],
            type=node["type"],
            size=15,
            confidence=0.5,
            properties=node.get("properties", {}),
            updated_at=None
        )
        for node in detail_result.get("connected_nodes", [])
    ]
    
    response = MemoryDetailResponse(
        node=memory_node,
        relations=detail_result.get("relations", []),
        connected_nodes=connected_nodes
    )
    
    logger.success(f"✅ 获取记忆节点详情成功: {len(connected_nodes)} 个相关节点")
    
    return ResponseUtil.success(data=response, message="获取记忆节点详情成功")


@router.post("/memory-stats", response_model=SuccessResponse[MemoryStatsResponse], summary="获取记忆统计信息")
async def get_memory_statistics(
    request: MemoryStatsRequest,
    current_user: User = Depends(get_current_active_user),
    digital_human_service: DigitalHumanService = Depends(get_digital_human_service),
    graph_service: GraphService = Depends(get_graph_service)
):
    """获取数字人的记忆统计信息"""
    digital_human = digital_human_service.get_digital_human_by_id(
        request.digital_human_id, 
        current_user.id
    )
    
    if not digital_human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数字人不存在或您无权限访问"
        )
    
    logger.info(f"📊 用户 {current_user.id} 获取数字人记忆统计: ID={request.digital_human_id}")
    
    stats = await graph_service.get_memory_statistics(
        digital_human_id=request.digital_human_id,
        include_timeline=request.include_timeline
    )
    
    response = MemoryStatsResponse(
        total_nodes=stats.get("total_nodes", 0),
        total_edges=stats.get("total_edges", 0),
        node_categories=stats.get("node_categories", {}),
        edge_types=stats.get("edge_types", {}),
        network_density=stats.get("network_density", 0),
        avg_connections_per_node=stats.get("avg_connections_per_node", 0),
        timeline=stats.get("timeline") if request.include_timeline else None
    )
    
    logger.success(f"✅ 获取记忆统计成功: {response.total_nodes} 个节点, {response.total_edges} 条关系")
    
    return ResponseUtil.success(data=response, message="获取记忆统计信息成功")


