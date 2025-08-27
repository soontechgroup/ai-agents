"""
图数据库分析API端点
所有操作使用POST请求，通过路径区分操作
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

# from app.core.models import User  # 暂时禁用认证
# from app.guards.auth import get_current_user  # 暂时禁用认证
from app.schemas.common_response import SuccessResponse
from app.utils.response import ResponseUtil
from app.dependencies.graph import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/analytics", tags=["Graph Analytics"])


# ==================== 请求模型 ====================

class StatisticsRequest(BaseModel):
    """统计请求（可扩展）"""
    include_nodes: bool = Field(True, description="是否包含节点统计")
    include_relationships: bool = Field(True, description="是否包含关系统计")
    filter_label: Optional[str] = Field(None, description="过滤特定标签")


class PersonAnalysisRequest(BaseModel):
    """人员分析请求"""
    person_name: str = Field(..., description="要分析的人员姓名")
    depth: int = Field(2, description="网络分析深度", ge=1, le=5)


# ==================== API端点 ====================

@router.post("/get-statistics", response_model=SuccessResponse, summary="获取系统统计")
async def get_system_statistics(
    request: StatisticsRequest = StatisticsRequest(),
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """获取图数据库系统统计信息"""
    stats = await service.get_system_statistics()
    
    # 根据请求参数过滤结果
    result = {}
    if request.include_nodes:
        result["nodes"] = stats.get("nodes", {})
        result["total_nodes"] = stats.get("total_nodes", 0)
    
    if request.include_relationships:
        result["relationships"] = stats.get("relationships", {})
        result["total_relationships"] = stats.get("total_relationships", 0)
    
    # 如果指定了标签过滤
    if request.filter_label and "nodes" in result:
        filtered_nodes = {k: v for k, v in result["nodes"].items() if k == request.filter_label}
        result["nodes"] = filtered_nodes
    
    return ResponseUtil.success(data=result)


@router.post("/analyze-person", response_model=SuccessResponse, summary="分析个人信息")
async def analyze_person(
    request: PersonAnalysisRequest,
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """分析指定人员的详细信息和关系网络"""
    try:
        from neomodel import db
        
        # 先查找人员
        from app.repositories.neomodel import PersonRepository
        repo = PersonRepository()
        persons = repo.find_by_name(request.person_name)
        
        if not persons:
            return ResponseUtil.error(message=f"找不到人物: {request.person_name}")
        
        person = persons[0]
        person_uid = person.uid
        
        # 获取人员的详细网络信息
        network_data = await service.get_person_network(person_uid, depth=request.depth)
        
        if not network_data:
            return ResponseUtil.error(message="获取人员网络信息失败")
        
        # 获取所有关系类型和数量
        rel_query = """
            MATCH (p:Person {uid: $uid})-[r]-()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
        """
        rel_results, _ = db.cypher_query(rel_query, {"uid": person_uid})
        
        relationships_summary = {}
        for row in rel_results:
            if row[0]:
                relationships_summary[row[0]] = row[1]
        
        # 获取直接关联的人员
        direct_query = """
            MATCH (p:Person {uid: $uid})-[r]-(other:Person)
            RETURN DISTINCT other.name as name, other.uid as uid, 
                   other.occupation as occupation, type(r) as relationship
            LIMIT 20
        """
        direct_results, _ = db.cypher_query(direct_query, {"uid": person_uid})
        
        direct_connections = []
        for row in direct_results:
            direct_connections.append({
                "name": row[0],
                "uid": row[1],
                "occupation": row[2],
                "relationship": row[3]
            })
        
        # 获取工作单位
        org_query = """
            MATCH (p:Person {uid: $uid})-[r:WORKS_AT]->(o:Organization)
            RETURN o.name as org_name, o.uid as org_uid, 
                   r.position as position, r.department as department
        """
        org_results, _ = db.cypher_query(org_query, {"uid": person_uid})
        
        organizations = []
        for row in org_results:
            organizations.append({
                "name": row[0],
                "uid": row[1],
                "position": row[2],
                "department": row[3]
            })
        
        # 构建分析结果
        analysis_result = {
            "person": network_data.get("person"),
            "statistics": {
                "total_connections": sum(relationships_summary.values()),
                "colleague_count": network_data["stats"]["colleague_count"],
                "network_size": network_data["stats"]["network_size"],
                "relationships_breakdown": relationships_summary
            },
            "direct_connections": direct_connections,
            "organizations": organizations,
            "network_depth": 2
        }
        
        return ResponseUtil.success(data=analysis_result)
        
    except Exception as e:
        return ResponseUtil.error(message=f"分析人员失败: {str(e)}")


@router.delete("/clear-all", response_model=SuccessResponse, summary="清空所有数据")
async def clear_all_data(
    service: GraphService = Depends(get_graph_service),
    # current_user: User = Depends(get_current_user)  # 暂时禁用认证
):
    """清空图数据库中的所有数据（谨慎使用）"""
    try:
        from neomodel import db
        
        # 删除所有节点和关系
        query = "MATCH (n) DETACH DELETE n"
        db.cypher_query(query)
        
        return ResponseUtil.success(message="所有数据已成功清空")
    except Exception as e:
        return ResponseUtil.error(message=f"清空数据失败: {str(e)}")