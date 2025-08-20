"""图数据库服务层"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from app.repositories.graph import GraphRepository

logger = logging.getLogger(__name__)


class GraphService:
    """图数据库服务类"""
    
    def __init__(self, graph: GraphRepository):
        self.graph = graph
    
    # ==================== 用户相关 ====================
    
    async def create_user_node(self, user_id: int, username: str, email: str) -> Dict[str, Any]:
        """创建用户节点"""
        try:
            user = self.graph.find_or_create_node(
                label='User',
                unique_property='user_id',
                unique_value=user_id,
                properties={
                    'user_id': user_id,
                    'username': username,
                    'email': email,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"用户节点创建/获取成功: {username} (ID: {user['id']})")
            return user
            
        except Exception as e:
            logger.error(f"创建用户节点失败: {str(e)}")
            raise
    
    async def create_digital_human_with_owner(
        self,
        digital_human_id: int,
        name: str,
        description: str,
        owner_user_id: int
    ) -> Dict[str, Any]:
        """创建数字人节点并建立与用户的关系"""
        try:
            # 确保用户节点存在
            user_node = self.graph.nodes.find_by_property('User', 'user_id', owner_user_id)
            if not user_node:
                logger.warning(f"未找到用户节点: {owner_user_id}")
                return None
            
            # 创建数字人节点并建立关系
            dh_node = self.graph.create_node_with_relationships(
                label='DigitalHuman',
                properties={
                    'digital_human_id': digital_human_id,
                    'name': name,
                    'description': description,
                    'created_at': datetime.now().isoformat()
                },
                connections=[
                    {
                        'from_id': user_node['id'],
                        'type': 'OWNS',
                        'direction': 'from',
                        'properties': {'since': datetime.now().isoformat()}
                    }
                ]
            )
            
            logger.info(f"创建数字人节点并建立关系: {name}")
            return dh_node
            
        except Exception as e:
            logger.error(f"创建数字人节点失败: {str(e)}")
            raise
    
    # ==================== 对话相关 ====================
    
    async def create_conversation_with_participants(
        self,
        conversation_id: str,
        user_id: int,
        digital_human_id: int,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建对话节点并建立与参与者的关系"""
        try:
            # 查找参与者节点
            user_node = self.graph.nodes.find_by_property('User', 'user_id', user_id)
            dh_node = self.graph.nodes.find_by_property('DigitalHuman', 'digital_human_id', digital_human_id)
            
            connections = []
            if user_node:
                connections.append({
                    'from_id': user_node['id'],
                    'type': 'PARTICIPATES_IN',
                    'direction': 'from'
                })
            
            if dh_node:
                connections.append({
                    'from_id': dh_node['id'],
                    'type': 'PARTICIPATES_IN',
                    'direction': 'from'
                })
            
            # 创建对话节点并建立所有关系
            conv_node = self.graph.create_node_with_relationships(
                label='Conversation',
                properties={
                    'conversation_id': conversation_id,
                    'topic': topic or 'General',
                    'started_at': datetime.now().isoformat()
                },
                connections=connections
            )
            
            logger.info(f"创建对话节点: {conversation_id}")
            return conv_node
            
        except Exception as e:
            logger.error(f"创建对话节点失败: {str(e)}")
            raise
    
    # ==================== 批量操作 ====================
    
    async def import_users_batch(self, users_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量导入用户"""
        try:
            nodes_data = []
            for user_data in users_data:
                nodes_data.append({
                    'label': 'User',
                    'properties': {
                        'user_id': user_data['id'],
                        'username': user_data['username'],
                        'email': user_data['email'],
                        'created_at': datetime.now().isoformat()
                    }
                })
            
            created_nodes = self.graph.create_nodes_batch(nodes_data)
            logger.info(f"批量创建 {len(created_nodes)} 个用户节点")
            
            return created_nodes
            
        except Exception as e:
            logger.error(f"批量导入用户失败: {str(e)}")
            return []
    
    # ==================== 查询功能 ====================
    
    async def get_user_profile_complete(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户完整画像"""
        try:
            user_node = self.graph.nodes.find_by_property('User', 'user_id', user_id)
            if not user_node:
                return None
            
            # 获取用户及其所有连接
            user_profile = self.graph.find_node_with_connections(
                user_node['id'],
                direction='outgoing'
            )
            
            # 分类连接信息
            if user_profile and 'connections' in user_profile:
                digital_humans = []
                conversations = []
                
                for conn in user_profile['connections']:
                    node = conn['node']
                    if 'DigitalHuman' in node.get('labels', []):
                        digital_humans.append(node)
                    elif 'Conversation' in node.get('labels', []):
                        conversations.append(node)
                
                user_profile['digital_humans'] = digital_humans
                user_profile['conversations'] = conversations
                user_profile['stats'] = {
                    'digital_human_count': len(digital_humans),
                    'conversation_count': len(conversations)
                }
            
            return user_profile
            
        except Exception as e:
            logger.error(f"获取用户画像失败: {str(e)}")
            return None
    
    async def get_digital_human_analytics(self, digital_human_id: int) -> Dict[str, Any]:
        """获取数字人分析数据"""
        try:
            # 获取基础信息
            dh_node = self.graph.nodes.find_by_property('DigitalHuman', 'digital_human_id', digital_human_id)
            if not dh_node:
                return {'error': 'Digital human not found'}
            
            # 获取统计数据
            stats_query = """
            MATCH (dh:DigitalHuman {digital_human_id: $dh_id})
            OPTIONAL MATCH (dh)-[:PARTICIPATES_IN]->(c:Conversation)
            OPTIONAL MATCH (u:User)-[:PARTICIPATES_IN]->(c)
            RETURN 
                count(DISTINCT c) as conversation_count,
                count(DISTINCT u) as unique_user_count,
                collect(DISTINCT u.username)[..5] as sample_users
            """
            
            stats = self.graph.execute_cypher(
                stats_query,
                {'dh_id': digital_human_id}
            )
            
            return {
                'digital_human': dh_node,
                'analytics': stats[0] if stats else {},
                'connections': self.graph.find_node_with_connections(dh_node['id'])
            }
            
        except Exception as e:
            logger.error(f"获取数字人分析失败: {str(e)}")
            return {'error': str(e)}
    
    async def clone_digital_human(
        self,
        original_id: int,
        new_name: str,
        new_owner_id: int
    ) -> Optional[Dict[str, Any]]:
        """克隆数字人"""
        try:
            # 查找原数字人
            original = self.graph.nodes.find_by_property(
                'DigitalHuman',
                'digital_human_id',
                original_id
            )
            if not original:
                return None
            
            # 克隆节点
            new_properties = {
                'name': new_name,
                'digital_human_id': f"{original_id}_clone_{datetime.now().timestamp()}",
                'cloned_from': original_id,
                'cloned_at': datetime.now().isoformat()
            }
            
            cloned = self.graph.clone_node(
                original['id'],
                new_properties,
                clone_relationships=False  # 不克隆关系
            )
            
            # 建立与新所有者的关系
            if cloned and new_owner_id:
                owner = self.graph.nodes.find_by_property('User', 'user_id', new_owner_id)
                if owner:
                    self.graph.relationships.create(
                        owner['id'],
                        cloned['id'],
                        'OWNS',
                        {'since': datetime.now().isoformat()}
                    )
            
            logger.info(f"成功克隆数字人: {new_name}")
            return cloned
            
        except Exception as e:
            logger.error(f"克隆数字人失败: {str(e)}")
            return None
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            stats = self.graph.get_statistics()
            
            # 添加更多统计信息
            additional_stats = {
                'active_conversations': self.graph.execute_cypher(
                    "MATCH (c:Conversation) WHERE c.ended_at IS NULL RETURN count(c) as count"
                ),
                'popular_digital_humans': self.graph.execute_cypher("""
                    MATCH (dh:DigitalHuman)-[:PARTICIPATES_IN]->(c:Conversation)
                    RETURN dh.name as name, count(c) as conversation_count
                    ORDER BY conversation_count DESC
                    LIMIT 5
                """)
            }
            
            stats['additional'] = additional_stats
            return stats
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            return {'error': str(e)}