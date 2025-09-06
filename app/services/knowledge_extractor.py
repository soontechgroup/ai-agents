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
识别文本中的实体和关系。

实体类型：人物、组织、地点、概念
输出格式：
- 实体：NAME|TYPE|DESCRIPTION
- 关系：SOURCE|TARGET|RELATION

文本：{text}
"""
    
    def _parse_output(self, output: str) -> Dict[str, List]:
        """解析 LLM 输出"""
        entities = []
        relationships = []
        
        for line in output.strip().split('\n'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == 3:
                    # 简单判断是实体还是关系
                    if any(t in parts[1].upper() for t in ['人物', 'PERSON', '组织', 'ORGANIZATION']):
                        entities.append({
                            "name": parts[0],
                            "type": parts[1],
                            "description": parts[2]
                        })
                    else:
                        relationships.append({
                            "source": parts[0],
                            "target": parts[1],
                            "description": parts[2]
                        })
        
        return {"entities": entities, "relationships": relationships}