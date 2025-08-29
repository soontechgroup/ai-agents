"""
事件仓储
"""

from typing import List
from datetime import datetime
from neomodel import db

from app.models.neomodel.nodes import Event
from app.repositories.neomodel.base import NeomodelRepository


class EventRepository(NeomodelRepository):
    """事件仓储"""
    
    def __init__(self):
        super().__init__(Event)
    
    def find_upcoming(self, limit: int = 10) -> List[Event]:
        """查找即将到来的事件"""
        query = """
            MATCH (e:Event)
            WHERE e.start_date >= $today
            RETURN e
            ORDER BY e.start_date
            LIMIT $limit
        """
        results, _ = db.cypher_query(
            query,
            {"today": datetime.now().date().isoformat(), "limit": limit}
        )
        return [Event.inflate(row[0]) for row in results]
    
    def find_past_events(self, limit: int = 10) -> List[Event]:
        """查找过去的事件"""
        query = """
            MATCH (e:Event)
            WHERE e.end_date < $today
            RETURN e
            ORDER BY e.end_date DESC
            LIMIT $limit
        """
        results, _ = db.cypher_query(
            query,
            {"today": datetime.now().date().isoformat(), "limit": limit}
        )
        return [Event.inflate(row[0]) for row in results]
    
    def find_by_date_range(self, start_date: str, end_date: str) -> List[Event]:
        """查找日期范围内的事件"""
        query = """
            MATCH (e:Event)
            WHERE e.start_date >= $start AND e.start_date <= $end
            RETURN e
            ORDER BY e.start_date
        """
        results, _ = db.cypher_query(
            query,
            {"start": start_date, "end": end_date}
        )
        return [Event.inflate(row[0]) for row in results]