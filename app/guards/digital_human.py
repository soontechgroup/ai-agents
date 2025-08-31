"""数字人权限验证守卫"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.models import User, DigitalHuman
from app.guards.auth import get_current_active_user
from app.dependencies.database import get_db
from app.core.logger import logger


async def verify_digital_human_owner(
    digital_human_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> DigitalHuman:
    """
    验证用户是否拥有指定的数字人
    
    Args:
        digital_human_id: 数字人ID
        current_user: 当前登录用户
        db: 数据库会话
    
    Returns:
        DigitalHuman: 验证通过的数字人对象
    
    Raises:
        HTTPException: 当数字人不存在或用户无权访问时
    """
    # 查询数字人
    digital_human = db.query(DigitalHuman).filter(
        DigitalHuman.id == digital_human_id
    ).first()
    
    # 检查数字人是否存在
    if not digital_human:
        logger.warning(f"数字人不存在: ID={digital_human_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数字人不存在（ID: {digital_human_id}）"
        )
    
    # 检查用户是否是数字人的所有者
    if digital_human.owner_id != current_user.id:
        logger.warning(
            f"用户 {current_user.id} 尝试访问不属于自己的数字人 {digital_human_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问该数字人的记忆"
        )
    
    # 检查数字人是否激活
    if not digital_human.is_active:
        logger.info(f"数字人未激活: ID={digital_human_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该数字人已被停用"
        )
    
    logger.info(f"用户 {current_user.id} 验证访问数字人 {digital_human_id} 成功")
    return digital_human


async def get_user_digital_human(
    digital_human_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> DigitalHuman:
    """
    获取用户拥有的数字人（简化版本的验证）
    
    Args:
        digital_human_id: 数字人ID
        current_user: 当前登录用户
        db: 数据库会话
    
    Returns:
        DigitalHuman: 用户拥有的数字人对象
    """
    return await verify_digital_human_owner(digital_human_id, current_user, db)


async def verify_digital_human_access(
    digital_human_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> DigitalHuman:
    """
    验证用户是否有权访问数字人（未来可扩展为包括共享权限）
    
    Args:
        digital_human_id: 数字人ID
        current_user: 当前登录用户
        db: 数据库会话
    
    Returns:
        DigitalHuman: 有权访问的数字人对象
    """
    # 目前只检查所有权，未来可以扩展为检查共享权限
    return await verify_digital_human_owner(digital_human_id, current_user, db)


class DigitalHumanGuard:
    """数字人守卫类 - 提供静态方法访问"""
    verify_owner = staticmethod(verify_digital_human_owner)
    get_digital_human = staticmethod(get_user_digital_human)
    verify_access = staticmethod(verify_digital_human_access)