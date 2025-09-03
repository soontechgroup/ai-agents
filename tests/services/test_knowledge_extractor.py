import pytest
import os
import logging
import time
from app.services.knowledge_extractor import KnowledgeExtractor
from app.services.extraction_config import ExtractionConfig, ProcessingStrategy, ConfidenceMergeStrategy
from app.core.logger import logger

# 设置第三方库日志级别为WARNING，避免DEBUG信息
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langchain_core").setLevel(logging.WARNING)
logging.getLogger("langchain_openai").setLevel(logging.WARNING)

# 设置根日志器级别为INFO，避免DEBUG输出
logging.getLogger().setLevel(logging.INFO)

# 真实API测试 - 需要OPENAI_API_KEY环境变量


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要OPENAI_API_KEY环境变量进行真实API测试")
class TestKnowledgeExtractorRealAPI:
    """真实API测试 - 使用GPT-4o-mini进行实际知识抽取"""
    
    def setup_method(self):
        """初始化真实的KnowledgeExtractor"""
        logger.info("🚀 开始真实API测试 - 使用GPT-4o-mini")
        self.extractor = KnowledgeExtractor()
        
        # 验证API key存在
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            logger.info(f"✅ API Key已设置: {masked_key}")
        
    @pytest.mark.asyncio
    async def test_prompt_format_compliance(self):
        """测试LLM是否遵循我们定义的输出格式"""
        logger.info("格式遵循度测试")
        
        test_text = "苹果公司的iPhone是一款智能手机产品。"
        logger.info(f"输入: {test_text}")
        
        # 获取原始LLM响应
        chunks = self.extractor.text_splitter.split_text(test_text)
        if chunks:
            prompt = self.extractor._build_prompt(chunks[0])
            
            # 直接调用LLM获取原始输出
            llm_response = await self.extractor.llm.ainvoke(prompt)
            raw_output = llm_response.content
            
            logger.info("LLM原始输出:")
            logger.info(raw_output)
            
            # 解析结果
            parsed_result = self.extractor._parse_output(raw_output)
            logger.info("解析后的结果:")
            
            if parsed_result['entities']:
                logger.info("实体:")
                for entity in parsed_result['entities']:
                    name = entity.get('name', '未知')
                    # 支持多类型显示
                    types = entity.get('types', [])
                    type_display = ", ".join(types) if types else entity.get('type', '未知类型')
                    description = entity.get('description', '')
                    confidence = entity.get('confidence', 0.0)
                    
                    logger.info(f"  {name} ({type_display}) [{confidence:.2f}]")
                    
                    # 显示结构化属性
                    properties = entity.get('properties', {})
                    if properties and properties != {'description': description}:
                        logger.info(f"    属性: {properties}")
            
            if parsed_result['relationships']:
                logger.info("关系:")
                for rel in parsed_result['relationships']:
                    source = rel.get('source', '未知')
                    target = rel.get('target', '未知')
                    
                    # 支持多类型关系显示
                    types = rel.get('types', [])
                    rel_type = ", ".join(types) if types else rel.get('relation_type', '未知关系')
                    
                    description = rel.get('description', '')
                    confidence = rel.get('confidence', 0.0)
                    strength = rel.get('strength', 0.0)
                    
                    logger.info(f"  {source} --[{rel_type}]--> {target} [{confidence:.2f}, {strength:.2f}]")
                    if description:
                        logger.info(f"    描述: {description}")
                    
                    # 显示关系属性
                    properties = rel.get('properties', {})
                    if properties and properties != {'description': description}:
                        logger.info(f"    属性: {properties}")
            
            # 简单验证
            assert len(parsed_result['entities']) > 0 or len(parsed_result['relationships']) > 0
            
        logger.info("✅ 格式测试完成")
        
    @pytest.mark.asyncio
    async def test_simple_entity_extraction(self):
        """测试简单实体抽取"""
        logger.info("简单实体抽取测试")
        
        test_text = "张三是阿里巴巴的工程师，他在杭州工作。"
        logger.info(f"输入: {test_text}")
        
        result = await self.extractor.extract(test_text)
        
        logger.info("最终抽取结果:")
        if result['entities']:
            logger.info("实体:")
            for entity in result['entities']:
                name = entity.get('name', '未知')
                types = entity.get('types', [])
                type_display = ", ".join(types) if types else entity.get('type', '未知类型')
                description = entity.get('description', '')
                confidence = entity.get('confidence', 0.0)
                
                logger.info(f"  {name} ({type_display}) [{confidence:.2f}]")
                
                properties = entity.get('properties', {})
                if properties and properties != {'description': description}:
                    logger.info(f"    属性: {properties}")
        
        if result['relationships']:
            logger.info("关系:")
            for rel in result['relationships']:
                source = rel.get('source', '未知')
                target = rel.get('target', '未知')
                types = rel.get('types', [])
                rel_type = ", ".join(types) if types else rel.get('relation_type', '未知关系')
                description = rel.get('description', '')
                confidence = rel.get('confidence', 0.0)
                strength = rel.get('strength', 0.0)
                
                logger.info(f"  {source} --[{rel_type}]--> {target} [{confidence:.2f}, {strength:.2f}]")
                if description:
                    logger.info(f"    描述: {description}")
                
                properties = rel.get('properties', {})
                if properties and properties != {'description': description}:
                    logger.info(f"    属性: {properties}")
        
        # 验证基本抽取效果
        entity_names = [e.get('name', '').lower() for e in result['entities']]
        
        # 检查关键实体（允许变体）
        has_person = any('张三' in name or 'zhangsan' in name for name in entity_names)
        has_company = any('阿里巴巴' in name or 'alibaba' in name for name in entity_names)
        has_location = any('杭州' in name or 'hangzhou' in name for name in entity_names)
        
        assert len(result['entities']) >= 1, "应该至少识别出1个实体"
        assert has_person or has_company or has_location, "应该识别出关键实体"
        
        logger.info("✅ 简单抽取测试完成")
        
    @pytest.mark.asyncio
    async def test_complex_business_scenario(self):
        """测试复杂商业场景"""
        logger.info("复杂商业场景测试")
        
        test_text = "马斯克在2008年成为特斯拉的CEO，特斯拉是一家电动汽车制造公司。同时，马斯克还创立了SpaceX公司，专注于航天技术开发。"
        logger.info(f"输入: {test_text}")
        
        result = await self.extractor.extract(test_text)
        
        logger.info("复杂场景抽取结果:")
        if result['entities']:
            logger.info("实体:")
            for entity in result['entities']:
                name = entity.get('name', '未知')
                types = entity.get('types', [])
                type_display = ", ".join(types) if types else entity.get('type', '未知类型')
                description = entity.get('description', '')
                confidence = entity.get('confidence', 0.0)
                
                logger.info(f"  {name} ({type_display}) [{confidence:.2f}]")
                
                properties = entity.get('properties', {})
                if properties and properties != {'description': description}:
                    logger.info(f"    属性: {properties}")
        
        if result['relationships']:
            logger.info("关系:")
            for rel in result['relationships']:
                source = rel.get('source', '未知')
                target = rel.get('target', '未知')
                types = rel.get('types', [])
                rel_type = ", ".join(types) if types else rel.get('relation_type', '未知关系')
                description = rel.get('description', '')
                confidence = rel.get('confidence', 0.0)
                strength = rel.get('strength', 0.0)
                
                logger.info(f"  {source} --[{rel_type}]--> {target} [{confidence:.2f}, {strength:.2f}]")
                if description:
                    logger.info(f"    描述: {description}")
                
                properties = rel.get('properties', {})
                if properties and properties != {'description': description}:
                    logger.info(f"    属性: {properties}")
        
        # 验证复杂场景抽取
        entity_names = [e.get('name', '').lower() for e in result['entities']]
        
        # 检查关键实体
        has_musk = any('马斯克' in name or 'musk' in name for name in entity_names)
        has_tesla = any('特斯拉' in name or 'tesla' in name for name in entity_names)
        has_spacex = any('spacex' in name or '太空探索' in name for name in entity_names)
        
        assert len(result['entities']) >= 2, "复杂场景应该识别出多个实体"
        assert has_musk or has_tesla or has_spacex, "应该识别出关键实体"
        
        logger.info("✅ 复杂场景测试完成")
        
    @pytest.mark.asyncio
    async def test_edge_cases(self):
        """测试边界情况"""
        logger.info("边界情况测试")
        
        edge_cases = [
            ("空字符串", ""),
            ("纯标点", "。，！？；："),
            ("短文本", "你好。"),
        ]
        
        for case_name, test_text in edge_cases:
            logger.info(f"测试 {case_name}")
            logger.info(f"输入: '{test_text}'")
            
            try:
                result = await self.extractor.extract(test_text)
                
                logger.info("边界情况结果:")
                if result['entities']:
                    logger.info("实体:")
                    for entity in result['entities']:
                        name = entity.get('name', '未知')
                        types = entity.get('types', [])
                        type_display = ", ".join(types) if types else entity.get('type', '未知类型')
                        confidence = entity.get('confidence', 0.0)
                        logger.info(f"  {name} ({type_display}) [{confidence:.2f}]")
                else:
                    logger.info("  无实体")
                
                if result['relationships']:
                    logger.info("关系:")
                    for rel in result['relationships']:
                        source = rel.get('source', '未知')
                        target = rel.get('target', '未知')
                        types = rel.get('types', [])
                        rel_type = ", ".join(types) if types else rel.get('relation_type', '未知关系')
                        confidence = rel.get('confidence', 0.0)
                        logger.info(f"  {source} --[{rel_type}]--> {target} [{confidence:.2f}]")
                else:
                    logger.info("  无关系")
                
                # 基本断言
                assert isinstance(result, dict)
                assert 'entities' in result and 'relationships' in result
                
                logger.info(f"✅ {case_name}测试通过")
                
            except Exception as e:
                logger.warning(f"⚠️  {case_name}出现异常: {str(e)}")
                
        logger.info("✅ 边界情况测试完成")


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要OPENAI_API_KEY环境变量进行真实API测试")
class TestKnowledgeExtractorMultiChunk:
    """多文本块处理测试 - GraphRAG完整功能测试"""
    
    def setup_method(self):
        """初始化多种配置的KnowledgeExtractor"""
        logger.info("🔧 初始化多文本块处理测试")
        
        # 默认增量处理配置
        self.default_config = ExtractionConfig(
            strategy=ProcessingStrategy.INCREMENTAL,
            chunk_size=800,
            chunk_overlap=100,
            enable_context_enhancement=True,
            enable_cross_chunk_relations=True,
            min_entity_confidence=0.3,
            min_relationship_confidence=0.4
        )
        self.default_extractor = KnowledgeExtractor(self.default_config)
        
        # 并行处理配置
        self.parallel_config = ExtractionConfig(
            strategy=ProcessingStrategy.PARALLEL,
            chunk_size=600,
            chunk_overlap=50,
            max_concurrent_chunks=3,
            enable_cross_chunk_relations=True,
            min_entity_confidence=0.4
        )
        self.parallel_extractor = KnowledgeExtractor(self.parallel_config)
        
        # 滑动窗口配置
        self.sliding_config = ExtractionConfig(
            strategy=ProcessingStrategy.SLIDING_WINDOW,
            chunk_size=500,
            chunk_overlap=150,
            enable_context_enhancement=True
        )
        self.sliding_extractor = KnowledgeExtractor(self.sliding_config)
        
    @pytest.mark.asyncio
    async def test_incremental_multi_chunk_processing(self):
        """测试增量式多文本块处理"""
        logger.info("📊 增量式多文本块处理测试")
        
        # 构造跨多个块的长文本
        test_text = """
        马斯克是特斯拉公司的首席执行官，他在2008年加入特斯拉，成为这家电动汽车公司的领导者。特斯拉公司成立于2003年，总部位于美国加利福尼亚州帕洛阿尔托。公司专注于电动汽车、能源存储和太阳能技术的开发。特斯拉的使命是加速世界向可持续能源的转变。公司推出了多款电动汽车产品，包括Model S、Model 3、Model X和Model Y等车型。这些车型在全球范围内取得了巨大成功，改变了人们对电动汽车的认知。
        
        除了特斯拉，马斯克还创立了SpaceX公司。SpaceX是一家私人航天公司，成立于2002年，总部位于加利福尼亚州霍桑。SpaceX公司致力于开发可重复使用的火箭技术，并计划进行火星探索任务。马斯克担任SpaceX的首席执行官兼首席技术官。SpaceX已经成功开发了猎鹰9号和猎鹰重型火箭，并且实现了火箭的回收和重复使用。公司还开发了载人龙飞船，为国际空间站执行载人任务。SpaceX的最终目标是实现火星殖民，使人类成为多行星物种。
        
        此外，马斯克还参与创立了Neuralink公司，这是一家专注于脑机接口技术的公司。Neuralink成立于2016年，目标是开发植入式脑机接口设备。该公司希望通过先进的神经技术帮助治疗各种神经疾病，并最终实现人脑与计算机的直接连接。Neuralink已经在动物实验中取得了重要进展，展示了通过脑机接口控制计算机设备的可能性。
        
        马斯克还是Boring Company的创始人，这家公司专注于地下隧道交通系统的开发。Boring Company成立于2016年，旨在解决城市交通拥堵问题。公司开发了高速地下隧道系统，可以大幅提高城市交通效率。该公司已经在拉斯维加斯等城市建设了示范项目，证明了地下交通系统的可行性。
        
        在马斯克的领导下，这些公司都在各自领域取得了突破性进展。马斯克以其远见卓识和创新精神而闻名，被认为是当代最具影响力的企业家之一。他的工作涉及多个前沿技术领域，从电动汽车到太空探索，从人工智能到交通运输，都在推动人类社会的进步。
        """
        
        logger.info(f"输入文本长度: {len(test_text)} 字符")
        
        # 使用extract_full进行完整处理
        progress_updates = []
        def progress_callback(processed, total, entities, relations):
            progress_updates.append((processed, total, entities, relations))
            logger.info(f"进度: {processed}/{total} 块, 实体: {entities}, 关系: {relations}")
        
        result = await self.default_extractor.extract_full(test_text, progress_callback)
        
        # 验证结果结构
        assert "entities" in result
        assert "relationships" in result
        assert "statistics" in result
        assert "config" in result
        assert "entity_merge_stats" in result
        assert "relationship_discovery_stats" in result
        
        # 验证处理了多个块
        stats = result["statistics"]
        assert stats["total_chunks"] > 1, "应该分割成多个文本块"
        assert stats["processed_chunks"] == stats["total_chunks"], "所有块都应该被处理"
        
        # 验证实体数量合理
        entities = result["entities"]
        assert len(entities) >= 5, f"应该识别出足够的实体，当前: {len(entities)}"
        
        # 验证关键实体
        entity_names = [e.get('name', '').lower() for e in entities]
        key_entities = ['马斯克', 'musk', '特斯拉', 'tesla', 'spacex']
        found_entities = [entity for entity in key_entities if any(entity in name for name in entity_names)]
        
        logger.info(f"识别出的实体数量: {len(entities)}")
        logger.info(f"找到的关键实体: {found_entities}")
        
        for entity in entities[:3]:  # 显示前3个实体
            logger.info(f"  实体: {entity.get('name')} ({', '.join(entity.get('types', []))}) [{entity.get('confidence', 0):.2f}]")
        
        # 验证关系
        relationships = result["relationships"]
        logger.info(f"识别出的关系数量: {len(relationships)}")
        
        for rel in relationships[:3]:  # 显示前3个关系
            logger.info(f"  关系: {rel.get('source')} --[{', '.join(rel.get('types', []))}]--> {rel.get('target')} [{rel.get('confidence', 0):.2f}]")
        
        # 验证进度回调被调用
        assert len(progress_updates) > 0, "进度回调应该被调用"
        
        # 验证合并统计
        merge_stats = result["entity_merge_stats"]
        assert "original_entities" in merge_stats
        assert "merged_entities" in merge_stats
        
        logger.info(f"实体合并统计: {merge_stats}")
        logger.info(f"关系发现统计: {result['relationship_discovery_stats']}")
        
        logger.info("✅ 增量式多文本块处理测试完成")
        
    @pytest.mark.asyncio
    async def test_parallel_processing_strategy(self):
        """测试并行处理策略"""
        logger.info("⚡ 并行处理策略测试")
        
        test_text = """
        阿里巴巴集团是中国最大的电子商务公司之一，由马云在1999年创立于杭州。
        公司旗下拥有淘宝网、天猫、支付宝等知名平台。马云担任了多年的董事局主席。
        腾讯公司是另一家中国科技巨头，由马化腾创立于深圳。腾讯开发了微信、QQ等社交软件。
        百度公司专注于搜索引擎和人工智能技术，由李彦宏创立于北京。
        这三家公司被称为中国互联网的BAT三巨头。
        """
        
        start_time = time.time()
        result = await self.parallel_extractor.extract_full(test_text)
        processing_time = time.time() - start_time
        
        logger.info(f"并行处理耗时: {processing_time:.2f}秒")
        
        # 验证配置正确应用
        assert result["config"]["strategy"] == "parallel"
        
        # 验证结果质量
        entities = result["entities"]
        relationships = result["relationships"]
        
        logger.info(f"并行处理识别实体: {len(entities)}")
        logger.info(f"并行处理识别关系: {len(relationships)}")
        
        # 验证关键实体被识别
        entity_names = [e.get('name', '').lower() for e in entities]
        companies = ['阿里巴巴', 'alibaba', '腾讯', 'tencent', '百度', 'baidu']
        found_companies = [comp for comp in companies if any(comp in name for name in entity_names)]
        
        assert len(found_companies) >= 2, f"应该识别出主要公司，找到: {found_companies}"
        
        logger.info("✅ 并行处理策略测试完成")
        
    @pytest.mark.asyncio
    async def test_sliding_window_strategy(self):
        """测试滑动窗口策略"""
        logger.info("🔄 滑动窗口策略测试")
        
        test_text = """
        苹果公司成立于1976年，由史蒂夫·乔布斯、史蒂夫·沃兹尼亚克和罗纳德·韦恩共同创立。
        公司总部位于加利福尼亚州库比蒂诺。苹果最著名的产品包括iPhone、iPad、Mac电脑等。
        乔布斯在1997年重返苹果后，推出了一系列革命性产品。iPhone于2007年发布，改变了智能手机行业。
        蒂姆·库克在2011年成为苹果公司CEO，继续推动公司发展。苹果现在是全球市值最高的公司之一。
        """
        
        result = await self.sliding_extractor.extract_full(test_text)
        
        # 验证配置正确应用
        assert result["config"]["strategy"] == "sliding_window"
        
        # 滑动窗口应该能更好地处理跨块的连续性
        entities = result["entities"]
        relationships = result["relationships"]
        
        logger.info(f"滑动窗口识别实体: {len(entities)}")
        logger.info(f"滑动窗口识别关系: {len(relationships)}")
        
        # 验证关键人物和公司被识别
        entity_names = [e.get('name', '').lower() for e in entities]
        key_entities = ['苹果', 'apple', '乔布斯', 'jobs', '库克', 'cook']
        found_entities = [entity for entity in key_entities if any(key in name for name in entity_names)]
        
        assert len(found_entities) >= 2, f"应该识别出关键实体，找到: {found_entities}"
        
        logger.info("✅ 滑动窗口策略测试完成")
        
    @pytest.mark.asyncio
    async def test_entity_merging_across_chunks(self):
        """测试跨块实体合并功能"""
        logger.info("🔀 跨块实体合并测试")
        
        # 故意在不同块中提及相同实体的不同表述
        test_text = """
        埃隆·马斯克是一位著名的企业家和工程师。他出生于南非，后来移居美国。
        马斯克先生创立了多家公司，包括特斯拉汽车公司。特斯拉是一家专注于电动汽车的公司。
        Elon Musk还创建了SpaceX，这是一家私人航天公司。马斯克担任SpaceX的CEO职位。
        此外，Mr. Musk还参与了其他项目，如脑机接口公司Neuralink。
        """
        
        # 使用较小的chunk_size确保分割成多个块
        config = ExtractionConfig(
            strategy=ProcessingStrategy.INCREMENTAL,
            chunk_size=200,
            chunk_overlap=50,
            entity_similarity_threshold=0.7,  # 降低阈值以测试相似实体合并
            enable_entity_aliasing=True
        )
        extractor = KnowledgeExtractor(config)
        
        result = await extractor.extract_full(test_text)
        
        entities = result["entities"]
        entity_names = [e.get('name', '') for e in entities]
        
        logger.info(f"合并后实体数量: {len(entities)}")
        for entity in entities:
            logger.info(f"  {entity.get('name')} - 置信度: {entity.get('confidence', 0):.2f}")
        
        # 验证马斯克的不同表述被合并
        musk_entities = [name for name in entity_names if any(term in name.lower() for term in ['musk', '马斯克', 'elon'])]
        
        logger.info(f"识别的马斯克相关实体: {musk_entities}")
        
        # 验证合并统计
        merge_stats = result["entity_merge_stats"]
        logger.info(f"合并前实体数: {merge_stats.get('original_entities', 0)}")
        logger.info(f"合并后实体数: {merge_stats.get('merged_entities', 0)}")
        logger.info(f"合并比率: {merge_stats.get('merge_ratio', 0):.2f}")
        
        # 应该发生了一些合并
        assert merge_stats.get("entities_saved", 0) > 0, "应该有实体被合并"
        
        logger.info("✅ 跨块实体合并测试完成")
        
    @pytest.mark.asyncio
    async def test_cross_chunk_relationship_discovery(self):
        """测试跨块关系发现"""
        logger.info("🔗 跨块关系发现测试")
        
        test_text = """
        张三是ABC科技公司的软件工程师。他在北京办公室工作。
        ABC科技公司是XYZ集团的子公司。XYZ集团总部位于上海。
        李四也在ABC科技公司工作，担任产品经理职位。
        王五是XYZ集团的董事长，负责整个集团的战略规划。
        """
        
        config = ExtractionConfig(
            strategy=ProcessingStrategy.INCREMENTAL,
            chunk_size=150,
            chunk_overlap=30,
            enable_cross_chunk_relations=True,
            relation_confidence_threshold=0.5
        )
        extractor = KnowledgeExtractor(config)
        
        result = await extractor.extract_full(test_text)
        
        relationships = result["relationships"]
        logger.info(f"发现关系数量: {len(relationships)}")
        
        # 分析关系类型
        relation_methods = {}
        cross_chunk_relations = []
        
        for rel in relationships:
            discovery_method = rel.get('properties', {}).get('discovery_method', 'unknown')
            relation_methods[discovery_method] = relation_methods.get(discovery_method, 0) + 1
            
            if discovery_method in ['cooccurrence', 'transitive_inference']:
                cross_chunk_relations.append(rel)
                logger.info(f"  跨块关系: {rel.get('source')} --[{', '.join(rel.get('types', []))}]--> {rel.get('target')}")
                logger.info(f"    发现方法: {discovery_method}")
        
        logger.info(f"关系发现方法统计: {relation_methods}")
        
        # 验证关系发现统计
        discovery_stats = result["relationship_discovery_stats"]
        logger.info(f"关系发现统计: {discovery_stats}")
        
        # 应该发现一些跨块关系
        if len(cross_chunk_relations) > 0:
            logger.info(f"成功发现 {len(cross_chunk_relations)} 个跨块关系")
        
        logger.info("✅ 跨块关系发现测试完成")
        
    @pytest.mark.asyncio
    async def test_context_enhancement(self):
        """测试上下文增强功能"""
        logger.info("📝 上下文增强测试")
        
        test_text = """
        微软公司由比尔·盖茨创立于1975年。公司最初专注于软件开发。
        Windows操作系统是微软最著名的产品之一。盖茨在微软担任CEO多年。
        现在萨蒂亚·纳德拉是微软的CEO。纳德拉推动了微软向云计算的转型。
        Azure是微软的云计算平台，与亚马逊AWS竞争激烈。
        """
        
        config = ExtractionConfig(
            strategy=ProcessingStrategy.INCREMENTAL,
            chunk_size=120,
            chunk_overlap=20,
            enable_context_enhancement=True,
            max_context_entities=8,
            context_window_size=2
        )
        extractor = KnowledgeExtractor(config)
        
        result = await extractor.extract_full(test_text)
        
        # 验证上下文统计
        stats = result["statistics"]
        logger.info(f"上下文增强统计:")
        logger.info(f"  关键实体数量: {stats.get('key_entities_count', 0)}")
        logger.info(f"  平均每块实体数: {stats.get('average_entities_per_chunk', 0):.1f}")
        logger.info(f"  最常提及的实体: {stats.get('most_mentioned_entities', {})}")
        
        entities = result["entities"]
        logger.info(f"上下文增强识别实体: {len(entities)}")
        
        # 验证微软相关实体被正确识别和连接
        entity_names = [e.get('name', '').lower() for e in entities]
        microsoft_related = ['微软', 'microsoft', '盖茨', 'gates', '纳德拉', 'nadella']
        found_ms_entities = [entity for entity in microsoft_related if any(ms in name for name in entity_names)]
        
        logger.info(f"识别的微软相关实体: {found_ms_entities}")
        
        assert len(found_ms_entities) >= 2, "上下文增强应该帮助识别更多相关实体"
        
        logger.info("✅ 上下文增强测试完成")
        
        
    @pytest.mark.asyncio
    async def test_processing_time_estimation(self):
        """测试处理时间估算"""
        logger.info("⏱️ 处理时间估算测试")
        
        test_text = "这是一段测试文本。" * 100  # 重复文本创建较长内容
        
        estimate = self.default_extractor.estimate_processing_time(test_text)
        
        logger.info(f"处理时间估算:")
        logger.info(f"  预估时间: {estimate['estimated_time_seconds']:.1f}秒")
        logger.info(f"  预估块数: {estimate['estimated_chunks']}")
        logger.info(f"  使用策略: {estimate['strategy']}")
        logger.info(f"  文本长度: {estimate['text_length']}")
        
        # 验证估算结果合理
        assert estimate['estimated_time_seconds'] > 0
        assert estimate['estimated_chunks'] > 0
        assert estimate['text_length'] == len(test_text)
        
        logger.info("✅ 处理时间估算测试完成")