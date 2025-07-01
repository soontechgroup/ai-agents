from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db, User
import os

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-abc123456")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# HTTP Bearer认证方案
security = HTTPBearer()

class JWTToken:
    """JWT Token工具类"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """
        创建访问令牌
        
        Args:
            data: 要编码的数据字典
            expires_delta: 过期时间差，默认为24小时
            
        Returns:
            str: JWT令牌字符串
        """
        to_encode = data.copy()
        
        # 设置过期时间
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # 添加标准JWT声明
        to_encode.update({
            "exp": expire,  # 过期时间
            "iat": datetime.now(timezone.utc),  # 签发时间
            "iss": "user-management-api"  # 发行者
        })
        
        # 生成JWT
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            dict: 解码后的payload数据
            
        Raises:
            HTTPException: 令牌无效时抛出异常
        """
        try:
            # 解码JWT
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # 获取用户ID
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的认证令牌",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户（依赖注入函数）
    
    Args:
        credentials: HTTP Bearer认证凭据
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 认证失败时抛出异常
    """
    # 验证JWT令牌
    payload = JWTToken.verify_token(credentials.credentials)
    
    # 获取用户ID
    user_id = payload.get("sub")
    
    # 从数据库查询用户
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取当前用户（可选，用于可能需要认证的接口）
    
    Args:
        credentials: HTTP Bearer认证凭据（可选）
        db: 数据库会话
        
    Returns:
        Optional[User]: 当前用户对象或None
    """
    if credentials is None:
        return None
    
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None 