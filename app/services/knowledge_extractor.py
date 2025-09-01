from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.logger import logger


class KnowledgeExtractor:
    """内部知识抽取服务，供其他服务调用"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=100
        )
    
    async def extract(self, text: str) -> Dict[str, List]:
        """抽取实体和关系（内部使用）"""
        
        chunks = self.text_splitter.split_text(text)
        
        # 简单实现：先处理第一个块
        if chunks:
            prompt = self._build_prompt(chunks[0])
            response = await self.llm.ainvoke(prompt)
            return self._parse_output(response.content)
        
        return {"entities": [], "relationships": []}
    
    def _build_prompt(self, text: str) -> str:
        """构建 GraphRAG 风格的提示词"""
        return f"""
你是一个智能助手，帮助用户构建知识图谱。请从以下文本中提取实体和关系。

## 实体识别
识别文本中的所有实体，包括但不限于：
- **人物**：个人、虚构角色、群体
- **组织**：公司、机构、团队、政府部门
- **地点**：地理位置、设施、地标
- **事件**：历史事件、活动、会议
- **概念**：抽象概念、理论、技术、产品
- **时间**：日期、时期、时代

## 关系抽取
识别实体之间的关系，包括但不限于：
- 社会关系（朋友、家人、同事）
- 组织关系（雇佣、隶属、合作）
- 空间关系（位于、邻近、包含）
- 时间关系（之前、之后、期间）
- 因果关系（导致、影响、产生）

## 输出格式
严格按照以下格式输出，每行一个实体或关系：

实体格式：
ENTITY|<实体名称>|<实体类型>|<实体描述>

关系格式：
RELATIONSHIP|<源实体>|<目标实体>|<关系类型>|<关系描述>

## 示例
输入文本："张三是阿里巴巴的工程师，他在杭州工作。"

输出：
ENTITY|张三|人物|阿里巴巴的工程师
ENTITY|阿里巴巴|组织|科技公司
ENTITY|杭州|地点|中国城市
RELATIONSHIP|张三|阿里巴巴|雇佣关系|张三在阿里巴巴担任工程师
RELATIONSHIP|张三|杭州|位于|张三在杭州工作

## 注意事项
1. 实体名称应该是原文中出现的具体名称
2. 实体类型选择最合适的类别
3. 描述应该简洁但信息丰富
4. 关系类型应该清晰明确
5. 避免重复的实体和关系

## 待处理文本
{text}
"""
    
    def _parse_output(self, output: str) -> Dict[str, List]:
        """解析 LLM 输出"""
        entities = []
        relationships = []
        
        for line in output.strip().split('\n'):
            if '|' not in line:
                continue
                
            parts = [p.strip() for p in line.split('|')]
            
            # 解析实体：ENTITY|名称|类型|描述
            if line.startswith('ENTITY') and len(parts) >= 4:
                entities.append({
                    "name": parts[1],
                    "type": parts[2],
                    "description": parts[3] if len(parts) > 3 else ""
                })
            
            # 解析关系：RELATIONSHIP|源|目标|关系类型|描述
            elif line.startswith('RELATIONSHIP') and len(parts) >= 4:
                relationships.append({
                    "source": parts[1],
                    "target": parts[2],
                    "relation_type": parts[3],
                    "description": parts[4] if len(parts) > 4 else ""
                })
        
        return {"entities": entities, "relationships": relationships}