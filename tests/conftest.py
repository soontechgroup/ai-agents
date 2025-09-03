import pytest
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# 配置 pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def sample_entity_output():
    """提供示例实体输出格式"""
    return """ENTITY|张三|人物|阿里巴巴的工程师
ENTITY|阿里巴巴|组织|科技公司
ENTITY|杭州|地点|中国城市"""


@pytest.fixture
def sample_relationship_output():
    """提供示例关系输出格式"""
    return """RELATIONSHIP|张三|阿里巴巴|雇佣关系|张三在阿里巴巴担任工程师
RELATIONSHIP|张三|杭州|位于|张三在杭州工作"""


@pytest.fixture
def sample_mixed_output():
    """提供混合的实体和关系输出"""
    return """ENTITY|张三|人物|阿里巴巴的工程师
ENTITY|阿里巴巴|组织|科技公司
ENTITY|杭州|地点|中国城市
RELATIONSHIP|张三|阿里巴巴|雇佣关系|张三在阿里巴巴担任工程师
RELATIONSHIP|张三|杭州|位于|张三在杭州工作"""


@pytest.fixture
def sample_extraction_result():
    """提供标准的抽取结果格式"""
    return {
        "entities": [
            {"name": "张三", "type": "人物", "description": "阿里巴巴的工程师"},
            {"name": "阿里巴巴", "type": "组织", "description": "科技公司"},
            {"name": "杭州", "type": "地点", "description": "中国城市"}
        ],
        "relationships": [
            {
                "source": "张三",
                "target": "阿里巴巴",
                "relation_type": "雇佣关系",
                "description": "张三在阿里巴巴担任工程师"
            },
            {
                "source": "张三",
                "target": "杭州",
                "relation_type": "位于",
                "description": "张三在杭州工作"
            }
        ]
    }