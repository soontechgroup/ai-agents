"""
项目仓储
"""

from typing import List

from app.models.neomodel.nodes import Project
from app.repositories.neomodel.base import NeomodelRepository


class ProjectRepository(NeomodelRepository):
    """项目仓储"""
    
    def __init__(self):
        super().__init__(Project)
    
    def find_active(self) -> List[Project]:
        """查找活动项目"""
        return self.find_all(status='active')
    
    def find_by_status(self, status: str) -> List[Project]:
        """按状态查找项目"""
        return self.find_all(status=status)
    
    def find_by_priority(self, priority: str) -> List[Project]:
        """按优先级查找项目"""
        return self.find_all(priority=priority)
    
    def get_with_participants(self, uid: str) -> dict:
        """获取项目及其参与者"""
        project = self.find_by_uid(uid)
        if project:
            participants = list(project.participants.all()) if hasattr(project, 'participants') else []
            return {
                "project": project.to_dict(),
                "participants": [p.to_dict() for p in participants],
                "participant_count": len(participants)
            }
        return None