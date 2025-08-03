from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.models import DigitalHuman, User
from app.schemas.digital_human import DigitalHumanCreate, DigitalHumanUpdate, DigitalHumanPageRequest, DigitalHumanPageResponse, DigitalHumanResponse
from app.schemas.CommonResponse import PaginationMeta
from typing import List, Optional, Tuple


class DigitalHumanService:
    """数字人服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_digital_human(self, digital_human_data: DigitalHumanCreate, user_id: int) -> DigitalHuman:
        """创建数字人"""
        # 检查用户是否存在
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 转换personality为字典格式
        personality_dict = None
        if digital_human_data.personality:
            personality_dict = digital_human_data.personality.dict()
        
        # 创建数字人
        db_digital_human = DigitalHuman(
            name=digital_human_data.name,
            short_description=digital_human_data.short_description,
            detailed_description=digital_human_data.detailed_description,
            type=digital_human_data.type,
            skills=digital_human_data.skills,
            personality=personality_dict,
            conversation_style=digital_human_data.conversation_style,
            temperature=digital_human_data.temperature,
            max_tokens=digital_human_data.max_tokens,
            owner_id=user_id
        )
        
        self.db.add(db_digital_human)
        self.db.commit()
        self.db.refresh(db_digital_human)
        
        return db_digital_human
    
    def get_digital_human_by_id(self, digital_human_id: int, user_id: int) -> Optional[DigitalHuman]:
        """根据ID获取数字人"""
        digital_human = self.db.query(DigitalHuman).filter(
            DigitalHuman.id == digital_human_id,
            DigitalHuman.owner_id == user_id
        ).first()
        
        if not digital_human:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数字人不存在或无权访问"
            )
        
        return digital_human
    
    def get_user_digital_humans(self, user_id: int) -> List[DigitalHuman]:
        """获取用户的所有数字人"""
        return self.db.query(DigitalHuman).filter(
            DigitalHuman.owner_id == user_id
        ).order_by(DigitalHuman.created_at.desc()).all()
    
    def update_digital_human(self, digital_human_id: int, digital_human_data: DigitalHumanUpdate, user_id: int) -> DigitalHuman:
        """更新数字人"""
        digital_human = self.get_digital_human_by_id(digital_human_id, user_id)
        
        # 更新数据
        update_data = digital_human_data.dict(exclude_unset=True)
        
        # 处理personality字段
        if 'personality' in update_data and update_data['personality']:
            update_data['personality'] = update_data['personality'].dict()
        
        for field, value in update_data.items():
            setattr(digital_human, field, value)
        
        self.db.commit()
        self.db.refresh(digital_human)
        
        return digital_human
    
    def delete_digital_human(self, digital_human_id: int, user_id: int) -> bool:
        """删除数字人"""
        digital_human = self.get_digital_human_by_id(digital_human_id, user_id)
        
        self.db.delete(digital_human)
        self.db.commit()
        
        return True
    
    def get_digital_humans_paginated(self, page_request: DigitalHumanPageRequest, user_id: Optional[int] = None, include_public: bool = True) -> Tuple[List[DigitalHuman], int]:
        """获取分页的数字人列表"""
        query = self.db.query(DigitalHuman)
        
        # 权限过滤：只显示用户自己的和公开的模板
        if user_id is not None:
            if include_public:
                query = query.filter(
                    or_(
                        DigitalHuman.owner_id == user_id,
                        DigitalHuman.is_public == True
                    )
                )
            else:
                query = query.filter(DigitalHuman.owner_id == user_id)
        elif include_public:
            query = query.filter(DigitalHuman.is_public == True)
        
        # 搜索功能
        if page_request.search:
            search_term = f"%{page_request.search}%"
            query = query.filter(
                or_(
                    DigitalHuman.name.ilike(search_term),
                    DigitalHuman.short_description.ilike(search_term),
                    DigitalHuman.detailed_description.ilike(search_term)
                )
            )
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page_request.page - 1) * page_request.size
        digital_humans = query.order_by(DigitalHuman.created_at.desc())\
                              .offset(offset)\
                              .limit(page_request.size)\
                              .all()
        
        return digital_humans, total