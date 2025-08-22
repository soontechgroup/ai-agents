"""
人物节点模型
"""

from typing import Optional, List
from datetime import date
from pydantic import Field, field_validator, EmailStr
import re

from ..base import Node
from ..types import Gender, EMAIL_PATTERN, PHONE_PATTERN, MAX_NAME_LENGTH, MAX_TAGS_COUNT


class PersonNode(Node):
    """
    人物节点模型
    表示系统中的个人实体
    """
    
    # 基本信息
    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        description="姓名"
    )
    
    gender: Optional[Gender] = Field(
        None,
        description="性别"
    )
    
    age: Optional[int] = Field(
        None,
        ge=0,
        le=150,
        description="年龄"
    )
    
    birth_date: Optional[date] = Field(
        None,
        description="出生日期"
    )
    
    # 联系信息
    email: Optional[EmailStr] = Field(
        None,
        description="电子邮箱"
    )
    
    phone: Optional[str] = Field(
        None,
        max_length=30,
        description="电话号码"
    )
    
    address: Optional[str] = Field(
        None,
        max_length=200,
        description="地址"
    )
    
    # 职业信息
    occupation: Optional[str] = Field(
        None,
        max_length=100,
        description="职业"
    )
    
    company: Optional[str] = Field(
        None,
        max_length=100,
        description="公司/组织"
    )
    
    department: Optional[str] = Field(
        None,
        max_length=100,
        description="部门"
    )
    
    position: Optional[str] = Field(
        None,
        max_length=100,
        description="职位"
    )
    
    # 教育背景
    education: Optional[str] = Field(
        None,
        max_length=200,
        description="教育背景"
    )
    
    school: Optional[str] = Field(
        None,
        max_length=100,
        description="毕业院校"
    )
    
    major: Optional[str] = Field(
        None,
        max_length=100,
        description="专业"
    )
    
    # 社交属性
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="个人简介"
    )
    
    interests: List[str] = Field(
        default_factory=list,
        max_length=MAX_TAGS_COUNT,
        description="兴趣爱好"
    )
    
    skills: List[str] = Field(
        default_factory=list,
        max_length=MAX_TAGS_COUNT,
        description="技能特长"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        max_length=MAX_TAGS_COUNT,
        description="标签"
    )
    
    # 社交媒体
    linkedin: Optional[str] = Field(
        None,
        max_length=100,
        description="LinkedIn账号"
    )
    
    twitter: Optional[str] = Field(
        None,
        max_length=50,
        description="Twitter账号"
    )
    
    github: Optional[str] = Field(
        None,
        max_length=50,
        description="GitHub账号"
    )
    
    website: Optional[str] = Field(
        None,
        max_length=200,
        description="个人网站"
    )
    
    # 其他属性
    nationality: Optional[str] = Field(
        None,
        max_length=50,
        description="国籍"
    )
    
    languages: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="语言能力"
    )
    
    avatar_url: Optional[str] = Field(
        None,
        max_length=500,
        description="头像URL"
    )
    
    # 验证器
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """验证电话号码格式"""
        if v and not re.match(PHONE_PATTERN, v):
            # 允许简单的数字格式
            if not v.replace('-', '').replace(' ', '').replace('+', '').isdigit():
                raise ValueError('Invalid phone number format')
        return v
    
    @field_validator('interests', 'skills', 'tags', 'languages')
    @classmethod
    def validate_list_items(cls, v):
        """验证列表项不重复且非空"""
        if v:
            # 去重
            unique_items = list(dict.fromkeys(v))
            # 过滤空字符串
            return [item for item in unique_items if item and item.strip()]
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        """验证网站URL格式"""
        if not v:
            return v
        v = v.strip()
        # 如果没有协议，添加https://
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        return v
    
    @field_validator('linkedin')
    @classmethod  
    def validate_linkedin(cls, v):
        """验证LinkedIn格式"""
        if not v:
            return v
        v = v.strip()
        # LinkedIn URL或用户名
        if not v.startswith('http'):
            v = f'https://linkedin.com/in/{v}'
        return v
    
    @field_validator('github')
    @classmethod
    def validate_github(cls, v):
        """验证GitHub格式"""
        if not v:
            return v
        v = v.strip()
        # GitHub用户名
        if '/' in v:
            # 如果是完整URL，提取用户名
            parts = v.rstrip('/').split('/')
            v = parts[-1]
        return v
    
    @field_validator('twitter')
    @classmethod
    def validate_twitter(cls, v):
        """验证Twitter格式"""
        if not v:
            return v
        v = v.strip()
        # Twitter用户名
        v = v.lstrip('@')
        return v
    
    def __init__(self, **data):
        """初始化人物节点"""
        super().__init__(**data)
        # 自动添加Person标签
        if "Person" not in self.labels:
            self.labels.append("Person")
        
        # 根据职业信息添加额外标签
        if self.occupation:
            # 可以根据职业添加特定标签
            occupation_lower = self.occupation.lower()
            if any(keyword in occupation_lower for keyword in ['engineer', 'developer', 'programmer']):
                if "Tech" not in self.labels:
                    self.labels.append("Tech")
            elif any(keyword in occupation_lower for keyword in ['manager', 'director', 'ceo', 'cto']):
                if "Management" not in self.labels:
                    self.labels.append("Management")
            elif any(keyword in occupation_lower for keyword in ['teacher', 'professor', 'educator']):
                if "Education" not in self.labels:
                    self.labels.append("Education")
    
    def get_display_name(self) -> str:
        """
        获取显示名称
        
        Returns:
            优先返回姓名，否则返回uid
        """
        return self.name or self.uid
    
    def get_contact_info(self) -> dict:
        """
        获取联系信息
        
        Returns:
            包含所有非空联系方式的字典
        """
        contact = {}
        if self.email:
            contact['email'] = self.email
        if self.phone:
            contact['phone'] = self.phone
        if self.address:
            contact['address'] = self.address
        if self.linkedin:
            contact['linkedin'] = self.linkedin
        if self.twitter:
            contact['twitter'] = self.twitter
        if self.github:
            contact['github'] = self.github
        if self.website:
            contact['website'] = self.website
        return contact
    
    def get_professional_info(self) -> dict:
        """
        获取职业信息
        
        Returns:
            包含所有职业相关信息的字典
        """
        professional = {}
        if self.occupation:
            professional['occupation'] = self.occupation
        if self.company:
            professional['company'] = self.company
        if self.department:
            professional['department'] = self.department
        if self.position:
            professional['position'] = self.position
        if self.skills:
            professional['skills'] = self.skills
        return professional
    
    def calculate_age(self) -> Optional[int]:
        """
        根据出生日期计算年龄
        
        Returns:
            计算得出的年龄，如果没有出生日期则返回None
        """
        if self.birth_date:
            from datetime import date
            today = date.today()
            age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            return age
        return self.age
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<PersonNode uid='{self.uid}' name='{self.name}' occupation='{self.occupation or 'N/A'}'>"