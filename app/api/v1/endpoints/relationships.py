"""
关系管理API端点
所有操作使用POST请求，通过路径区分操作
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.schemas.graph.relationship import EmploymentRequest, FriendshipRequest, PathRequest
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/relationships", tags=["Relationships"])


# ==================== 请求模型 ====================

class ListRelationshipsRequest(BaseModel):
    """列出关系请求"""
    relationship_type: Optional[str] = Field(None, description="关系类型过滤")
    limit: int = Field(100, ge=1, le=500, description="返回数量限制")


# ==================== API端点 ====================

@router.post("/add-employment", response_model=SuccessResponse, summary="添加雇佣关系")
async def add_employment(
    request: EmploymentRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """添加人员与组织的雇佣关系"""
    success = await service.add_employment(
        request.person_uid,
        request.organization_uid,
        request.position,
        request.department
    )
    if success:
        return ResponseUtil.success(message="雇佣关系添加成功")
    return ResponseUtil.error(message="添加失败，请检查人员和组织是否存在")


@router.post("/add-friendship", response_model=SuccessResponse, summary="添加朋友关系")
async def add_friendship(
    request: FriendshipRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """添加两个人之间的朋友关系"""
    try:
        # 如果传入的是名字而不是UID，先查找人物
        from app.repositories.neomodel import PersonRepository
        from app.core.logger import logger
        
        repo = PersonRepository()
        
        person1_uid = request.person1_uid
        person2_uid = request.person2_uid
        
        logger.info(f"尝试添加朋友关系: {person1_uid} <-> {person2_uid}")
        
        # 检查是否是名字（不是UUID格式）
        import re
        uuid_pattern = re.compile(r'^[a-f0-9]{32}$')
        
        if not uuid_pattern.match(person1_uid):
            # 可能是名字，尝试查找
            persons = repo.find_by_name(person1_uid)
            if persons:
                person1_uid = persons[0].uid
                logger.info(f"将名字 {request.person1_uid} 转换为UID: {person1_uid}")
            else:
                logger.error(f"找不到人物: {request.person1_uid}")
                return ResponseUtil.error(message=f"找不到人物: {request.person1_uid}")
        
        if not uuid_pattern.match(person2_uid):
            # 可能是名字，尝试查找
            persons = repo.find_by_name(person2_uid)
            if persons:
                person2_uid = persons[0].uid
                logger.info(f"将名字 {request.person2_uid} 转换为UID: {person2_uid}")
            else:
                logger.error(f"找不到人物: {request.person2_uid}")
                return ResponseUtil.error(message=f"找不到人物: {request.person2_uid}")
        
        # 验证两个人物是否确实存在
        person1 = repo.find_by_uid(person1_uid)
        person2 = repo.find_by_uid(person2_uid)
        
        if not person1:
            logger.error(f"UID {person1_uid} 对应的人物不存在")
            return ResponseUtil.error(message=f"人物1不存在: {person1_uid}")
        
        if not person2:
            logger.error(f"UID {person2_uid} 对应的人物不存在")
            return ResponseUtil.error(message=f"人物2不存在: {person2_uid}")
        
        logger.info(f"找到两个人物: {person1.name} 和 {person2.name}")
        
        try:
            logger.info(f"准备调用service.add_friendship")
            success = await service.add_friendship(person1_uid, person2_uid)
            logger.info(f"service.add_friendship返回: {success}")
            
            if success:
                logger.success(f"成功添加朋友关系: {person1.name} <-> {person2.name}")
                return ResponseUtil.success(message="朋友关系添加成功")
            
            logger.error(f"服务层添加朋友关系失败")
            return ResponseUtil.error(message="添加失败")
        except Exception as service_error:
            logger.error(f"调用服务层时发生异常: {str(service_error)}")
            logger.error(f"异常类型: {type(service_error).__name__}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return ResponseUtil.error(message=f"服务调用失败: {str(service_error)}")
    except Exception as e:
        logger.exception(f"添加关系异常: {str(e)}")
        return ResponseUtil.error(message=f"添加关系失败: {str(e)}")


@router.post("/list", response_model=SuccessResponse, summary="获取所有关系")
async def list_relationships(
    request: ListRelationshipsRequest = ListRelationshipsRequest(),
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取图数据库中的所有关系"""
    try:
        from neomodel import db
        from app.core.logger import logger
        
        # 构建查询
        if request.relationship_type:
            query = f"""
                MATCH (a)-[r:{request.relationship_type}]->(b)
                RETURN id(a) as from_id, a.uid as from_uid, a.name as from_name,
                       id(b) as to_id, b.uid as to_uid, b.name as to_name,
                       type(r) as type, properties(r) as properties
                LIMIT {request.limit}
            """
        else:
            query = f"""
                MATCH (a)-[r]->(b)
                WHERE labels(a)[0] = 'Person' OR labels(a)[0] = 'Organization'
                RETURN id(a) as from_id, a.uid as from_uid, a.name as from_name,
                       id(b) as to_id, b.uid as to_uid, b.name as to_name,
                       type(r) as type, properties(r) as properties
                LIMIT {request.limit}
            """
        
        results, _ = db.cypher_query(query)
        
        relationships = []
        for row in results:
            relationships.append({
                "from": row[1] or str(row[0]),  # 使用uid或id
                "from_name": row[2],
                "to": row[4] or str(row[3]),    # 使用uid或id
                "to_name": row[5],
                "type": row[6],
                "properties": row[7] if row[7] else {}
            })
        
        logger.info(f"获取到 {len(relationships)} 个关系")
        
        return ResponseUtil.success(data={
            "relationships": relationships,
            "total": len(relationships)
        })
        
    except Exception as e:
        logger.exception(f"获取关系列表失败: {str(e)}")
        return ResponseUtil.error(message=f"获取关系失败: {str(e)}")


@router.post("/find-shortest-path", response_model=SuccessResponse, summary="查找最短路径")
async def find_shortest_path(
    request: PathRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """查找两个人之间的最短路径"""
    path = await service.find_shortest_path(
        request.from_uid,
        request.to_uid
    )
    if path:
        return ResponseUtil.success(data=path)
    return ResponseUtil.error(message="未找到连接路径")