"""
人员仓储
"""

from typing import List, Optional
import logging
from neomodel import db

from app.models.neomodel.nodes import Person
from app.repositories.neomodel.base import NeomodelRepository

logger = logging.getLogger(__name__)


class PersonRepository(NeomodelRepository):
    """人员仓储"""
    
    def __init__(self):
        super().__init__(Person)
    
    def find_by_name(self, name: str) -> List[Person]:
        """通过姓名查找"""
        try:
            return Person.nodes.filter(name=name).all()
        except Exception as e:
            logger.error(f"查找人员失败: {str(e)}")
            return []
    
    def find_by_email(self, email: str) -> Optional[Person]:
        """通过邮箱查找"""
        return self.find_by_property(email=email)
    
    def find_by_skills(self, skills: List[str]) -> List[Person]:
        """通过技能查找"""
        query = """
            MATCH (p:Person)
            WHERE any(skill IN $skills WHERE skill IN p.skills)
            RETURN p
        """
        results, _ = db.cypher_query(query, {"skills": skills})
        return [Person.inflate(row[0]) for row in results]
    
    def find_colleagues(self, uid: str) -> List[Person]:
        """查找同事"""
        query = """
            MATCH (p:Person {uid: $uid})-[:WORKS_AT]->(org:Organization)
            <-[:WORKS_AT]-(colleague:Person)
            WHERE colleague.uid <> $uid
            RETURN DISTINCT colleague
        """
        results, _ = db.cypher_query(query, {"uid": uid})
        return [Person.inflate(row[0]) for row in results]
    
    def find_network(self, uid: str, depth: int = 2) -> List[Person]:
        """查找社交网络"""
        query = f"""
            MATCH (p:Person {{uid: $uid}})-[:KNOWS*1..{depth}]-(other:Person)
            WHERE other.uid <> $uid
            RETURN DISTINCT other
        """
        results, _ = db.cypher_query(query, {"uid": uid})
        return [Person.inflate(row[0]) for row in results]