"""
组织节点模型
"""

from typing import Optional, List
from datetime import date
from pydantic import Field, field_validator, model_validator, HttpUrl

from ..base import Node
from ..types import OrganizationType, MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_TAGS_COUNT


class OrganizationNode(Node):
    """
    组织节点模型
    表示公司、机构、团队等组织实体
    """
    
    # 基本信息
    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        description="组织名称"
    )
    
    type: OrganizationType = Field(
        default=OrganizationType.COMPANY,
        description="组织类型"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="组织描述"
    )
    
    # 组织详情
    industry: Optional[str] = Field(
        None,
        max_length=100,
        description="所属行业"
    )
    
    size: Optional[int] = Field(
        None,
        ge=1,
        le=10000000,
        description="组织规模（人数）"
    )
    
    founded_date: Optional[date] = Field(
        None,
        description="成立日期"
    )
    
    registration_number: Optional[str] = Field(
        None,
        max_length=100,
        description="注册号/统一社会信用代码"
    )
    
    # 联系信息
    email: Optional[str] = Field(
        None,
        max_length=100,
        description="官方邮箱"
    )
    
    phone: Optional[str] = Field(
        None,
        max_length=30,
        description="联系电话"
    )
    
    address: Optional[str] = Field(
        None,
        max_length=200,
        description="地址"
    )
    
    headquarters: Optional[str] = Field(
        None,
        max_length=100,
        description="总部所在地"
    )
    
    # 网络presence
    website: Optional[HttpUrl] = Field(
        None,
        description="官方网站"
    )
    
    linkedin: Optional[str] = Field(
        None,
        max_length=100,
        description="LinkedIn页面"
    )
    
    twitter: Optional[str] = Field(
        None,
        max_length=50,
        description="Twitter账号"
    )
    
    # 财务信息
    revenue: Optional[float] = Field(
        None,
        ge=0,
        description="年营收（默认货币单位）"
    )
    
    valuation: Optional[float] = Field(
        None,
        ge=0,
        description="估值"
    )
    
    funding_stage: Optional[str] = Field(
        None,
        max_length=50,
        description="融资阶段"
    )
    
    # 组织结构
    parent_org: Optional[str] = Field(
        None,
        max_length=100,
        description="母公司/上级组织"
    )
    
    subsidiaries: List[str] = Field(
        default_factory=list,
        max_items=100,
        description="子公司/下属组织"
    )
    
    departments: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="部门列表"
    )
    
    # 标签和分类
    tags: List[str] = Field(
        default_factory=list,
        max_items=MAX_TAGS_COUNT,
        description="标签"
    )
    
    certifications: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="认证资质"
    )
    
    products: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="主要产品/服务"
    )
    
    # 其他属性
    logo_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Logo URL"
    )
    
    is_public: Optional[bool] = Field(
        None,
        description="是否上市公司"
    )
    
    stock_symbol: Optional[str] = Field(
        None,
        max_length=10,
        description="股票代码"
    )
    
    # 验证器
    @field_validator('size')
    @classmethod
    def validate_size(cls, v):
        """验证组织规模的合理性"""
        # 基本验证，具体的类型相关验证可以在model_validator中进行
        return v
    
    @field_validator('founded_date')
    @classmethod
    def validate_founded_date(cls, v):
        """验证成立日期不能是未来"""
        if v:
            from datetime import date
            if v > date.today():
                raise ValueError('Founded date cannot be in the future')
        return v
    
    @field_validator('subsidiaries', 'departments', 'tags', 'certifications', 'products')
    @classmethod
    def validate_list_items(cls, v):
        """验证列表项不重复且非空"""
        if v:
            # 去重
            unique_items = list(dict.fromkeys(v))
            # 过滤空字符串
            return [item for item in unique_items if item and item.strip()]
        return v
    
    @field_validator('stock_symbol')
    @classmethod
    def validate_stock_symbol(cls, v):
        """验证股票代码格式"""
        if v:
            # 股票代码通常是大写字母
            return v.upper()
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """验证邮箱格式"""
        if v:
            import re
            from ..types import EMAIL_PATTERN
            if not re.match(EMAIL_PATTERN, v):
                raise ValueError('Invalid email format')
        return v
    
    def __init__(self, **data):
        """初始化组织节点"""
        super().__init__(**data)
        # 自动添加Organization标签
        if "Organization" not in self.labels:
            self.labels.append("Organization")
        
        # 根据组织类型添加额外标签
        if self.type:
            type_label = self.type.value.capitalize()
            if type_label not in self.labels:
                self.labels.append(type_label)
        
        # 根据行业添加标签
        if self.industry:
            industry_lower = self.industry.lower()
            if any(keyword in industry_lower for keyword in ['tech', 'software', 'internet', 'ai']):
                if "Tech" not in self.labels:
                    self.labels.append("Tech")
            elif any(keyword in industry_lower for keyword in ['finance', 'bank', 'insurance']):
                if "Finance" not in self.labels:
                    self.labels.append("Finance")
            elif any(keyword in industry_lower for keyword in ['health', 'medical', 'pharma']):
                if "Healthcare" not in self.labels:
                    self.labels.append("Healthcare")
    
    def get_display_name(self) -> str:
        """
        获取显示名称
        
        Returns:
            组织名称
        """
        return self.name
    
    def get_size_category(self) -> str:
        """
        获取规模分类
        
        Returns:
            规模分类：微型、小型、中型、大型、巨型
        """
        if not self.size:
            return "unknown"
        elif self.size < 10:
            return "micro"
        elif self.size < 50:
            return "small"
        elif self.size < 250:
            return "medium"
        elif self.size < 1000:
            return "large"
        else:
            return "enterprise"
    
    def calculate_age(self) -> Optional[int]:
        """
        计算组织年龄
        
        Returns:
            成立至今的年数
        """
        if self.founded_date:
            from datetime import date
            today = date.today()
            return today.year - self.founded_date.year
        return None
    
    def is_subsidiary(self) -> bool:
        """
        判断是否为子公司
        
        Returns:
            是否有母公司
        """
        return bool(self.parent_org)
    
    def has_subsidiaries(self) -> bool:
        """
        判断是否有子公司
        
        Returns:
            是否有子公司
        """
        return bool(self.subsidiaries)
    
    def get_financial_info(self) -> dict:
        """
        获取财务信息
        
        Returns:
            包含所有财务相关信息的字典
        """
        financial = {}
        if self.revenue is not None:
            financial['revenue'] = self.revenue
        if self.valuation is not None:
            financial['valuation'] = self.valuation
        if self.funding_stage:
            financial['funding_stage'] = self.funding_stage
        if self.is_public is not None:
            financial['is_public'] = self.is_public
        if self.stock_symbol:
            financial['stock_symbol'] = self.stock_symbol
        return financial
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<OrganizationNode uid='{self.uid}' name='{self.name}' type='{self.type.value}' industry='{self.industry or 'N/A'}'>"