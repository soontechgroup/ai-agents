from typing import List, Dict, Any, Optional, Callable
import asyncio
import time
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.logger import logger
from app.models.graph.dynamic_entity import DynamicEntity
from app.models.graph.dynamic_relationship import DynamicRelationship
from app.models.graph.dynamic_factory import DynamicGraphFactory
from app.services.extraction_config import ExtractionConfig, ProcessingStrategy
from app.services.entity_merger import EntityMerger
from app.services.relationship_discoverer import CrossChunkRelationshipDiscoverer
from app.services.context_manager import ContextManager


class KnowledgeExtractor:
    """内部知识抽取服务，供其他服务调用"""
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()  # 使用默认配置
        
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0
        )
        
        # 基于配置创建文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        # 初始化组件
        self.entity_merger = EntityMerger(self.config)
        self.relationship_discoverer = CrossChunkRelationshipDiscoverer(self.config)
        self.context_manager = ContextManager(self.config)
        self.graph_factory = DynamicGraphFactory()
        
        # 处理状态
        self.processing_stats = {
            "total_chunks": 0,
            "processed_chunks": 0,
            "total_entities": 0,
            "total_relationships": 0,
            "processing_time": 0.0
        }
    
    async def extract(self, text: str) -> Dict[str, List]:
        """抽取实体和关系（简单版本，向后兼容）"""
        
        chunks = self.text_splitter.split_text(text)
        
        # 简单实现：先处理第一个块
        if chunks:
            prompt = self._build_prompt(chunks[0])
            response = await self.llm.ainvoke(prompt)
            return self._parse_output(response.content)
        
        return {"entities": [], "relationships": []}
    
    async def extract_full(self, text: str, 
                          progress_callback: Optional[Callable[[int, int, int, int], None]] = None) -> Dict[str, Any]:
        """
        完整的GraphRAG知识抽取，支持多文本块处理
        
        Args:
            text: 输入文本
            progress_callback: 进度回调函数 (processed_chunks, total_chunks, entities_found, relationships_found)
        
        Returns:
            完整的抽取结果，包含统计信息
        """
        start_time = time.time()
        self._reset_processing_stats()
        self.context_manager.clear_context()
        
        # 文本分割
        chunks = self.text_splitter.split_text(text)
        if not chunks:
            logger.warning("文本分割后无内容")
            return self._build_empty_result()
        
        self.processing_stats["total_chunks"] = len(chunks)
        
        logger.info(f"开始完整GraphRAG抽取，共 {len(chunks)} 个文本块")
        
        # 根据策略选择处理方式
        if self.config.strategy == ProcessingStrategy.INCREMENTAL:
            result = await self._process_incremental(chunks, progress_callback)
        elif self.config.strategy == ProcessingStrategy.PARALLEL:
            result = await self._process_parallel(chunks, progress_callback)
        elif self.config.strategy == ProcessingStrategy.SLIDING_WINDOW:
            result = await self._process_sliding_window(chunks, progress_callback)
        else:
            logger.warning(f"未知处理策略: {self.config.strategy}，使用增量式处理")
            result = await self._process_incremental(chunks, progress_callback)
        
        # 计算总处理时间
        self.processing_stats["processing_time"] = time.time() - start_time
        
        # 添加统计信息
        result["statistics"] = self._get_processing_statistics()
        result["config"] = {
            "strategy": self.config.strategy.value,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "enable_cross_chunk_relations": self.config.enable_cross_chunk_relations
        }
        
        logger.info(f"GraphRAG抽取完成，耗时 {self.processing_stats['processing_time']:.2f}s，"
                   f"实体: {self.processing_stats['total_entities']}，"
                   f"关系: {self.processing_stats['total_relationships']}")
        
        return result
    
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
- **SKILL**：技能、能力、专长

### 领域特定类型（可自由创造）：
- **TECH_COMPANY**、**AI_RESEARCHER**、**SOFTWARE_ENGINEER**
- **BLOCKCHAIN_EXPERT**、**STARTUP_FOUNDER** 等
- 根据上下文自主判断和创造新类型

## 实体属性提取要求

### 对于 PERSON 类型，请尽可能提取以下属性：
- **age**：年龄（如果文中提到）
- **gender**：性别（如果文中提到）
- **occupation**：职业/职位
- **education**：教育背景
- **skills**：技能列表
- **experience**：工作经验
- **nationality**：国籍
- **location**：所在地

### 对于 ORGANIZATION 类型，请提取：
- **industry**：所属行业
- **size**：规模（员工数量等）
- **founded**：成立时间
- **headquarters**：总部位置
- **type**：组织类型（公司/非营利/政府等）

### 对于其他类型，根据上下文提取相关属性

## 关系类型系统

### 标准关系类型：
- **WORKS_FOR**（工作关系）- 属性：position（职位）、since（开始时间）、department（部门）
- **LOCATED_IN**（位置关系）  
- **PART_OF**（隶属关系）
- **CREATED_BY**（创建关系）
- **COMPETES_WITH**（竞争关系）
- **COLLABORATES_WITH**（合作关系）
- **KNOWS**（认识关系）- 属性：relationship_type（朋友/同事/家人等）
- **HAS_SKILL**（拥有技能）- 属性：proficiency（熟练度）、years（年限）

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
    
    # ==================== 完整GraphRAG处理方法 ====================
    
    async def _process_incremental(self, chunks: List[str], 
                                  progress_callback: Optional[Callable[[int, int, int, int], None]]) -> Dict[str, Any]:
        """增量式处理策略"""
        
        all_chunk_results = []
        merged_entities = {}
        
        for chunk_index, chunk in enumerate(chunks):
            try:
                # 构建增强的上下文提示
                enhanced_chunk = self.context_manager.build_chunk_context(chunk, chunk_index)
                
                # 处理单个块
                chunk_result = await self._process_single_chunk(enhanced_chunk, chunk_index)
                all_chunk_results.append(chunk_result)
                
                # 增量合并实体
                chunk_entities = self.graph_factory.create_from_extraction(chunk_result)[0]
                if chunk_entities:
                    current_merged = self.entity_merger.merge_entities(
                        list(merged_entities.values()) + chunk_entities
                    )
                    merged_entities.update(current_merged)
                
                # 更新上下文
                self.context_manager.update_context(chunk_index, chunk_result, merged_entities)
                
                # 更新统计和进度
                self.processing_stats["processed_chunks"] += 1
                self.processing_stats["total_entities"] = len(merged_entities)
                
                if progress_callback:
                    progress_callback(
                        self.processing_stats["processed_chunks"],
                        self.processing_stats["total_chunks"],
                        len(merged_entities),
                        0  # 关系会在最后统一处理
                    )
                
            except Exception as e:
                logger.error(f"处理块 {chunk_index} 时出错: {str(e)}")
                if not self.config.continue_on_chunk_error:
                    raise
        
        # 发现跨块关系
        cross_chunk_relations = self.relationship_discoverer.discover_relationships(
            all_chunk_results, merged_entities
        )
        
        # 合并所有关系
        all_relations = []
        for chunk_result in all_chunk_results:
            chunk_relations = self.graph_factory.create_from_extraction(chunk_result)[1]
            all_relations.extend(chunk_relations)
        
        all_relations.extend(cross_chunk_relations)
        
        self.processing_stats["total_relationships"] = len(all_relations)
        
        return self._build_final_result(merged_entities, all_relations, all_chunk_results)
    
    async def _process_parallel(self, chunks: List[str],
                               progress_callback: Optional[Callable[[int, int, int, int], None]]) -> Dict[str, Any]:
        """并行处理策略"""
        
        # 创建并发任务
        semaphore = asyncio.Semaphore(self.config.max_concurrent_chunks)
        tasks = []
        
        async def process_chunk_with_semaphore(chunk: str, index: int):
            async with semaphore:
                return await self._process_single_chunk(chunk, index)
        
        for i, chunk in enumerate(chunks):
            task = process_chunk_with_semaphore(chunk, i)
            tasks.append(task)
        
        # 并行执行
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        valid_results = []
        for i, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                logger.error(f"并行处理块 {i} 失败: {str(result)}")
                if not self.config.continue_on_chunk_error:
                    raise result
            else:
                valid_results.append(result)
                self.processing_stats["processed_chunks"] += 1
        
        # 合并所有结果
        all_entities = []
        all_relations = []
        
        for chunk_result in valid_results:
            entities, relations = self.graph_factory.create_from_extraction(chunk_result)
            all_entities.extend(entities)
            all_relations.extend(relations)
        
        # 实体合并
        merged_entities = self.entity_merger.merge_entities(all_entities)
        
        # 发现跨块关系
        if self.config.enable_cross_chunk_relations:
            cross_chunk_relations = self.relationship_discoverer.discover_relationships(
                valid_results, merged_entities
            )
            all_relations.extend(cross_chunk_relations)
        
        self.processing_stats["total_entities"] = len(merged_entities)
        self.processing_stats["total_relationships"] = len(all_relations)
        
        return self._build_final_result(merged_entities, all_relations, valid_results)
    
    async def _process_sliding_window(self, chunks: List[str],
                                     progress_callback: Optional[Callable[[int, int, int, int], None]]) -> Dict[str, Any]:
        """滑动窗口处理策略"""
        
        # 滑动窗口处理，每次处理重叠的块
        window_size = min(3, len(chunks))  # 窗口大小
        all_chunk_results = []
        merged_entities = {}
        
        # 确保步长至少为1，避免除零错误
        step_size = max(1, window_size // 2)
        for start_idx in range(0, len(chunks), step_size):
            end_idx = min(start_idx + window_size, len(chunks))
            window_chunks = chunks[start_idx:end_idx]
            
            # 合并窗口内的文本
            combined_text = "\n\n".join(window_chunks)
            
            # 处理合并的文本
            window_result = await self._process_single_chunk(combined_text, start_idx)
            all_chunk_results.append(window_result)
            
            # 更新合并实体
            window_entities = self.graph_factory.create_from_extraction(window_result)[0]
            if window_entities:
                current_merged = self.entity_merger.merge_entities(
                    list(merged_entities.values()) + window_entities
                )
                merged_entities.update(current_merged)
            
            self.processing_stats["processed_chunks"] += len(window_chunks)
            
            if progress_callback:
                progress_callback(
                    min(self.processing_stats["processed_chunks"], len(chunks)),
                    len(chunks),
                    len(merged_entities),
                    0
                )
        
        # 处理关系
        all_relations = []
        for chunk_result in all_chunk_results:
            chunk_relations = self.graph_factory.create_from_extraction(chunk_result)[1]
            all_relations.extend(chunk_relations)
        
        # 发现跨窗口关系
        if self.config.enable_cross_chunk_relations:
            cross_chunk_relations = self.relationship_discoverer.discover_relationships(
                all_chunk_results, merged_entities
            )
            all_relations.extend(cross_chunk_relations)
        
        self.processing_stats["total_entities"] = len(merged_entities)
        self.processing_stats["total_relationships"] = len(all_relations)
        
        return self._build_final_result(merged_entities, all_relations, all_chunk_results)
    
    async def _process_single_chunk(self, chunk: str, chunk_index: int) -> Dict[str, Any]:
        """处理单个文本块"""
        
        chunk_start_time = time.time()
        
        try:
            prompt = self._build_prompt(chunk)
            response = await self.llm.ainvoke(prompt)
            result = self._parse_output(response.content)
            
            # 添加处理元信息
            result["chunk_index"] = chunk_index
            result["processing_time"] = time.time() - chunk_start_time
            result["chunk_length"] = len(chunk)
            
            return result
            
        except Exception as e:
            logger.error(f"处理块 {chunk_index} 时出错: {str(e)}")
            return {
                "entities": [],
                "relationships": [],
                "chunk_index": chunk_index,
                "processing_time": time.time() - chunk_start_time,
                "error": str(e)
            }
    
    def _build_final_result(self, merged_entities: Dict[str, DynamicEntity], 
                           all_relations: List[DynamicRelationship],
                           chunk_results: List[Dict]) -> Dict[str, Any]:
        """构建最终结果"""
        
        # 过滤低质量实体和关系
        filtered_entities = {
            name: entity for name, entity in merged_entities.items()
            if entity.confidence >= self.config.min_entity_confidence
        }
        
        filtered_relations = [
            rel for rel in all_relations
            if rel.confidence >= self.config.min_relationship_confidence
        ]
        
        # 转换为输出格式
        entities_output = []
        for entity in filtered_entities.values():
            entities_output.append({
                "name": entity.name,
                "types": entity.types,
                "type": "|".join(entity.types),
                "properties": entity.properties,
                "confidence": entity.confidence,
                "sources": entity.sources,
                "description": entity.properties.get("description", "")
            })
        
        relationships_output = []
        for rel in filtered_relations:
            relationships_output.append({
                "source": rel.source_name,
                "target": rel.target_name,
                "types": rel.relationship_types,
                "relation_type": "|".join(rel.relationship_types),
                "properties": rel.properties,
                "confidence": rel.confidence,
                "strength": rel.strength,
                "description": rel.properties.get("description", "")
            })
        
        return {
            "entities": entities_output,
            "relationships": relationships_output,
            "chunk_results": chunk_results if self.config.log_intermediate_results else [],
            "entity_merge_stats": self.entity_merger.get_merge_statistics(
                sum(len(cr.get("entities", [])) for cr in chunk_results),
                len(filtered_entities)
            ),
            "relationship_discovery_stats": self.relationship_discoverer.get_discovery_statistics(all_relations)
        }
    
    def _build_empty_result(self) -> Dict[str, Any]:
        """构建空结果"""
        return {
            "entities": [],
            "relationships": [],
            "statistics": self._get_processing_statistics(),
            "config": {"strategy": self.config.strategy.value}
        }
    
    def _reset_processing_stats(self) -> None:
        """重置处理统计"""
        self.processing_stats = {
            "total_chunks": 0,
            "processed_chunks": 0,
            "total_entities": 0,
            "total_relationships": 0,
            "processing_time": 0.0
        }
    
    def _get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        stats = self.processing_stats.copy()
        
        if stats["total_chunks"] > 0:
            stats["chunks_success_rate"] = stats["processed_chunks"] / stats["total_chunks"]
            stats["avg_processing_time_per_chunk"] = stats["processing_time"] / stats["processed_chunks"] if stats["processed_chunks"] > 0 else 0
        
        # 添加上下文管理统计
        context_stats = self.context_manager.get_context_statistics()
        stats.update(context_stats)
        
        return stats
    
    # ==================== 配置和实用方法 ====================
    
    def update_config(self, new_config: ExtractionConfig) -> None:
        """更新配置"""
        self.config = new_config
        
        # 重新初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        # 重新初始化组件
        self.entity_merger = EntityMerger(self.config)
        self.relationship_discoverer = CrossChunkRelationshipDiscoverer(self.config)
        self.context_manager = ContextManager(self.config)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取当前处理统计"""
        return self._get_processing_statistics()
    
    def get_memory_usage(self) -> float:
        """获取当前内存使用量(MB) - 简单实用的内存检查"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            logger.warning("psutil未安装，无法获取内存使用量")
            return 0.0
        except Exception as e:
            logger.warning(f"获取内存使用量失败: {str(e)}")
            return 0.0
    
    def estimate_processing_time(self, text: str) -> Dict[str, Any]:
        """估算处理时间"""
        chunks = self.text_splitter.split_text(text)
        
        # 基于经验公式估算
        base_time_per_chunk = 2.0  # 秒
        parallelism_factor = min(self.config.max_concurrent_chunks, len(chunks))
        
        if self.config.strategy == ProcessingStrategy.PARALLEL:
            estimated_time = (len(chunks) / parallelism_factor) * base_time_per_chunk
        elif self.config.strategy == ProcessingStrategy.SLIDING_WINDOW:
            estimated_time = len(chunks) * base_time_per_chunk * 1.5  # 滑动窗口开销更大
        else:
            estimated_time = len(chunks) * base_time_per_chunk
        
        return {
            "estimated_time_seconds": estimated_time,
            "estimated_chunks": len(chunks),
            "strategy": self.config.strategy.value,
            "text_length": len(text)
        }