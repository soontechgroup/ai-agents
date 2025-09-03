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
你是一个智能知识图谱助手，从文本中提取实体和关系。请使用动态类型系统，支持多重类型和丰富属性。

## 实体类型系统

### 基础类型（推荐使用）：
- **PERSON**：个人、虚构角色、群体
- **ORGANIZATION**：公司、机构、团队、政府部门  
- **LOCATION**：地理位置、设施、地标
- **EVENT**：历史事件、活动、会议
- **CONCEPT**：抽象概念、理论、技术
- **PRODUCT**：产品、服务、工具
- **TEMPORAL**：时间、日期、时期

### 领域特定类型（可自由创造）：
- **TECH_COMPANY**、**AI_RESEARCHER**、**SOFTWARE_ENGINEER**
- **BLOCKCHAIN_EXPERT**、**STARTUP_FOUNDER** 等
- 根据上下文自主判断和创造新类型

## 关系类型系统

### 标准关系类型：
- **WORKS_FOR**（工作关系）
- **LOCATED_IN**（位置关系）  
- **PART_OF**（隶属关系）
- **CREATED_BY**（创建关系）
- **COMPETES_WITH**（竞争关系）
- **COLLABORATES_WITH**（合作关系）

### 可扩展关系类型：
根据上下文创造具体的关系类型，如：**FOUNDED_BY**、**INVESTED_IN**、**MENTORS** 等

## 输出格式（JSON格式）

实体格式：
ENTITY|{{"name":"实体名称","types":["TYPE1","TYPE2"],"properties":{{"key":"value"}},"confidence":0.9}}

关系格式：
RELATIONSHIP|{{"source":"源实体","target":"目标实体","types":["REL_TYPE"],"properties":{{"key":"value"}},"confidence":0.9,"strength":0.8}}

## 示例
输入文本："马斯克在2008年成为特斯拉的CEO，特斯拉是一家电动汽车制造公司。"

输出：
ENTITY|{{"name":"马斯克","types":["PERSON","CEO","ENTREPRENEUR"],"properties":{{"full_name":"埃隆·马斯克","role":"CEO","company":"特斯拉"}},"confidence":0.95}}
ENTITY|{{"name":"特斯拉","types":["ORGANIZATION","TECH_COMPANY","AUTOMOTIVE"],"properties":{{"industry":"电动汽车","type":"制造公司","founded":"2003"}},"confidence":0.95}}
RELATIONSHIP|{{"source":"马斯克","target":"特斯拉","types":["LEADS","WORKS_FOR"],"properties":{{"role":"CEO","start_year":"2008","relationship_nature":"leadership"}},"confidence":0.9,"strength":0.9}}

## 属性设计原则
1. **实体属性**：职位、公司、技能、经验、教育背景等
2. **关系属性**：开始时间、职位、部门、持续时长等  
3. **置信度**：基于文本明确程度（0.1-1.0）
4. **关系强度**：关系的重要程度（0.1-1.0）

## 注意事项
1. 使用JSON格式，确保格式正确
2. 类型可以多个，用数组表示
3. 属性要丰富但准确，基于文本内容
4. 置信度要合理评估
5. 可以创造新的类型，但要有意义

## 待处理文本
{text}
"""
    
    def _parse_output(self, output: str) -> Dict[str, List]:
        """解析 LLM 输出，支持新的JSON格式"""
        import json
        
        entities = []
        relationships = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            if '|' not in line:
                continue
                
            parts = line.split('|', 1)  # 只分割一次，保留JSON部分
            if len(parts) != 2:
                continue
                
            prefix = parts[0].strip()
            json_part = parts[1].strip()
            
            try:
                # 尝试解析JSON格式
                if prefix == 'ENTITY' and json_part.startswith('{'):
                    entity_data = json.loads(json_part)
                    # 转换为标准格式，兼容原有接口
                    entities.append({
                        "name": entity_data.get("name", ""),
                        "type": "|".join(entity_data.get("types", [])) if entity_data.get("types") else "",
                        "types": entity_data.get("types", []),  # 新增：支持多类型
                        "description": entity_data.get("properties", {}).get("description", ""),
                        "properties": entity_data.get("properties", {}),  # 新增：结构化属性
                        "confidence": entity_data.get("confidence", 0.5)  # 新增：置信度
                    })
                
                elif prefix == 'RELATIONSHIP' and json_part.startswith('{'):
                    rel_data = json.loads(json_part)
                    relationships.append({
                        "source": rel_data.get("source", ""),
                        "target": rel_data.get("target", ""),
                        "relation_type": "|".join(rel_data.get("types", [])) if rel_data.get("types") else "",
                        "types": rel_data.get("types", []),  # 新增：支持多类型
                        "description": rel_data.get("properties", {}).get("description", ""),
                        "properties": rel_data.get("properties", {}),  # 新增：结构化属性
                        "confidence": rel_data.get("confidence", 0.5),  # 新增：置信度
                        "strength": rel_data.get("strength", 0.5)  # 新增：关系强度
                    })
                    
            except (json.JSONDecodeError, KeyError) as e:
                # JSON解析失败，尝试使用旧格式解析
                parts_old = line.split('|')
                if len(parts_old) >= 3 and parts_old[0].strip() == 'ENTITY':
                    entities.append({
                        "name": parts_old[1].strip() if len(parts_old) > 1 else "",
                        "type": parts_old[2].strip() if len(parts_old) > 2 else "",
                        "types": [parts_old[2].strip()] if len(parts_old) > 2 and parts_old[2].strip() else [],
                        "description": parts_old[3].strip() if len(parts_old) > 3 else "",
                        "properties": {"description": parts_old[3].strip() if len(parts_old) > 3 else ""},
                        "confidence": 0.5
                    })
                elif len(parts_old) >= 4 and parts_old[0].strip() == 'RELATIONSHIP':
                    relationships.append({
                        "source": parts_old[1].strip() if len(parts_old) > 1 else "",
                        "target": parts_old[2].strip() if len(parts_old) > 2 else "",
                        "relation_type": parts_old[3].strip() if len(parts_old) > 3 else "",
                        "types": [parts_old[3].strip()] if len(parts_old) > 3 and parts_old[3].strip() else [],
                        "description": parts_old[4].strip() if len(parts_old) > 4 else "",
                        "properties": {"description": parts_old[4].strip() if len(parts_old) > 4 else ""},
                        "confidence": 0.5,
                        "strength": 0.5
                    })
                logger.warning(f"解析行失败，使用旧格式: {line[:50]}... 错误: {str(e)}")
        
        return {"entities": entities, "relationships": relationships}