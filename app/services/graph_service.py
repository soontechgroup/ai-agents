"""
图数据库服务层
处理数字人项目中的图数据逻辑
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from app.utils.neo4j_util import neo4j_util

logger = logging.getLogger(__name__)


class GraphService:
    """图数据库服务类"""
    
    def __init__(self):
        self.neo4j = neo4j_util
    
    # ==================== 用户相关 ====================
    
    async def create_user_node(self, user_id: int, username: str, email: str) -> Dict[str, Any]:
        """
        创建用户节点
        
        Args:
            user_id: 用户ID（MySQL中的ID）
            username: 用户名
            email: 邮箱
        
        Returns:
            创建的用户节点
        """
        try:
            # 先检查是否已存在
            existing = self.neo4j.find_node_by_property('User', 'user_id', user_id)
            if existing:
                logger.info(f"用户节点已存在: {user_id}")
                return existing
            
            # 创建新节点
            node = self.neo4j.create_node('User', {
                'user_id': user_id,
                'username': username,
                'email': email,
                'created_at': datetime.now().isoformat()
            })
            
            logger.info(f"创建用户节点成功: {username} (ID: {node['id']})")
            return node
            
        except Exception as e:
            logger.error(f"创建用户节点失败: {str(e)}")
            raise
    
    async def create_digital_human_node(
        self,
        digital_human_id: int,
        name: str,
        description: str,
        owner_user_id: int
    ) -> Dict[str, Any]:
        """
        创建数字人节点并建立与用户的关系
        
        Args:
            digital_human_id: 数字人ID（MySQL中的ID）
            name: 数字人名称
            description: 描述
            owner_user_id: 拥有者用户ID
        
        Returns:
            创建的数字人节点
        """
        try:
            # 创建数字人节点
            dh_node = self.neo4j.create_node('DigitalHuman', {
                'digital_human_id': digital_human_id,
                'name': name,
                'description': description,
                'created_at': datetime.now().isoformat()
            })
            
            # 查找用户节点
            user_node = self.neo4j.find_node_by_property('User', 'user_id', owner_user_id)
            
            if user_node:
                # 创建 OWNS 关系
                self.neo4j.create_relationship(
                    user_node['id'],
                    dh_node['id'],
                    'OWNS',
                    {'since': datetime.now().isoformat()}
                )
                logger.info(f"创建数字人节点并建立关系: {name}")
            else:
                logger.warning(f"未找到用户节点: {owner_user_id}")
            
            return dh_node
            
        except Exception as e:
            logger.error(f"创建数字人节点失败: {str(e)}")
            raise
    
    # ==================== 对话相关 ====================
    
    async def create_conversation_node(
        self,
        conversation_id: str,
        user_id: int,
        digital_human_id: int,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建对话节点并建立关系
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            digital_human_id: 数字人ID
            topic: 对话主题
        
        Returns:
            创建的对话节点
        """
        try:
            # 创建对话节点
            conv_node = self.neo4j.create_node('Conversation', {
                'conversation_id': conversation_id,
                'topic': topic or 'General',
                'started_at': datetime.now().isoformat()
            })
            
            # 查找用户和数字人节点
            user_node = self.neo4j.find_node_by_property('User', 'user_id', user_id)
            dh_node = self.neo4j.find_node_by_property('DigitalHuman', 'digital_human_id', digital_human_id)
            
            # 创建关系
            if user_node:
                self.neo4j.create_relationship(
                    user_node['id'],
                    conv_node['id'],
                    'PARTICIPATES_IN'
                )
            
            if dh_node:
                self.neo4j.create_relationship(
                    dh_node['id'],
                    conv_node['id'],
                    'PARTICIPATES_IN'
                )
            
            logger.info(f"创建对话节点: {conversation_id}")
            return conv_node
            
        except Exception as e:
            logger.error(f"创建对话节点失败: {str(e)}")
            raise
    
    async def add_message_to_conversation(
        self,
        conversation_id: str,
        message_content: str,
        sender_type: str  # 'user' 或 'digital_human'
    ) -> Dict[str, Any]:
        """
        添加消息到对话
        
        Args:
            conversation_id: 对话ID
            message_content: 消息内容
            sender_type: 发送者类型
        
        Returns:
            创建的消息节点
        """
        try:
            # 创建消息节点
            msg_node = self.neo4j.create_node('Message', {
                'content': message_content,
                'sender_type': sender_type,
                'timestamp': datetime.now().isoformat()
            })
            
            # 查找对话节点
            conv_node = self.neo4j.find_node_by_property('Conversation', 'conversation_id', conversation_id)
            
            if conv_node:
                # 创建 CONTAINS 关系
                self.neo4j.create_relationship(
                    conv_node['id'],
                    msg_node['id'],
                    'CONTAINS',
                    {'order': datetime.now().timestamp()}
                )
            
            return msg_node
            
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}")
            raise
    
    # ==================== 查询功能 ====================
    
    async def get_user_digital_humans(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户拥有的所有数字人
        
        Args:
            user_id: 用户ID
        
        Returns:
            数字人列表
        """
        try:
            user_node = self.neo4j.find_node_by_property('User', 'user_id', user_id)
            if not user_node:
                return []
            
            # 查找所有通过 OWNS 关系连接的数字人
            digital_humans = self.neo4j.find_connected_nodes(
                user_node['id'],
                'OWNS',
                'outgoing'
            )
            
            return digital_humans
            
        except Exception as e:
            logger.error(f"获取用户数字人失败: {str(e)}")
            return []
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        获取对话中的所有消息
        
        Args:
            conversation_id: 对话ID
        
        Returns:
            消息列表
        """
        try:
            conv_node = self.neo4j.find_node_by_property('Conversation', 'conversation_id', conversation_id)
            if not conv_node:
                return []
            
            # 查找所有消息
            messages = self.neo4j.find_connected_nodes(
                conv_node['id'],
                'CONTAINS',
                'outgoing'
            )
            
            # 按时间戳排序
            messages.sort(key=lambda x: x['properties'].get('timestamp', ''))
            
            return messages
            
        except Exception as e:
            logger.error(f"获取对话消息失败: {str(e)}")
            return []
    
    async def find_similar_users(self, user_id: int) -> List[Dict[str, Any]]:
        """
        查找有相似兴趣的用户（基于共同的数字人交互）
        
        Args:
            user_id: 用户ID
        
        Returns:
            相似用户列表
        """
        try:
            query = """
            MATCH (u1:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation)<-[:PARTICIPATES_IN]-(dh:DigitalHuman)
            MATCH (u2:User)-[:PARTICIPATES_IN]->(c2:Conversation)<-[:PARTICIPATES_IN]-(dh)
            WHERE u1 <> u2
            RETURN DISTINCT u2, count(dh) as common_dh_count
            ORDER BY common_dh_count DESC
            LIMIT 10
            """
            
            results = self.neo4j.execute_query(query, {'user_id': user_id})
            
            similar_users = []
            for record in results:
                if 'u2' in record:
                    user_data = dict(record['u2'])
                    user_data['common_count'] = record.get('common_dh_count', 0)
                    similar_users.append(user_data)
            
            return similar_users
            
        except Exception as e:
            logger.error(f"查找相似用户失败: {str(e)}")
            return []
    
    async def get_popular_digital_humans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最受欢迎的数字人（基于对话数量）
        
        Args:
            limit: 返回数量限制
        
        Returns:
            数字人列表
        """
        try:
            query = """
            MATCH (dh:DigitalHuman)-[:PARTICIPATES_IN]->(c:Conversation)
            RETURN dh, count(c) as conversation_count
            ORDER BY conversation_count DESC
            LIMIT $limit
            """
            
            results = self.neo4j.execute_query(query, {'limit': limit})
            
            popular_dhs = []
            for record in results:
                if 'dh' in record:
                    dh_data = dict(record['dh'])
                    dh_data['conversation_count'] = record.get('conversation_count', 0)
                    popular_dhs.append(dh_data)
            
            return popular_dhs
            
        except Exception as e:
            logger.error(f"获取热门数字人失败: {str(e)}")
            return []


# 创建服务实例
graph_service = GraphService()