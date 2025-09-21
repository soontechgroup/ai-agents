# Pydantic 数据验证库

## 📚 使用说明

项目使用 Pydantic 进行数据验证和序列化，提供类型安全的数据模型。

## 🛠 框架配置

### 安装依赖
```bash
pip install pydantic[email]
```

### 基本使用示例
```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Dict
from enum import Enum

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    skills: Optional[List[str]] = Field(default=[])

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v.lower()

class DigitalHumanType(str, Enum):
    ASSISTANT = "专业助手"
    TEACHER = "智能老师"

class DigitalHumanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: DigitalHumanType = Field(default=DigitalHumanType.ASSISTANT)
    skills: List[str] = Field(default=[])
    temperature: float = Field(default=0.7, ge=0, le=2)

    @field_validator('skills')
    @classmethod
    def validate_skills(cls, v):
        if len(v) > 20:
            raise ValueError('技能不能超过20个')
        return list(set(v))  # 去重
```

## 💻 项目应用

### 数据模型定义
```python
# app/schemas/digital_human.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class DigitalHumanType(str, Enum):
    ASSISTANT = "专业助手"
    TEACHER = "智能老师"

class DigitalHumanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: DigitalHumanType = Field(default=DigitalHumanType.ASSISTANT)
    skills: List[str] = Field(default=[])
    temperature: float = Field(default=0.7, ge=0, le=2)

    @field_validator('skills')
    @classmethod
    def validate_skills(cls, v):
        if len(v) > 20:
            raise ValueError('技能不能超过20个')
        return list(set(v))

class DigitalHumanResponse(BaseModel):
    id: int
    name: str
    type: str
    owner_id: int
    skills: List[str]
    created_at: datetime

    class Config:
        orm_mode = True
```

### 配置管理
```python
# app/core/config.py
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    PROJECT_NAME: str = Field(default="AI Agents")
    DEBUG: bool = Field(default=False)
    DATABASE_URL: str = Field(..., description="数据库连接URL")
    SECRET_KEY: str = Field(..., description="JWT密钥")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API密钥")

    class Config:
        env_file = ".env"

settings = Settings()
```

Pydantic 为项目提供强大的数据验证、序列化和配置管理能力。