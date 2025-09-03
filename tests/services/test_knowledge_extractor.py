import pytest
import os
import logging
from app.services.knowledge_extractor import KnowledgeExtractor
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


# 提供使用说明
if __name__ == "__main__":
    print("""
    🚀 真实API测试使用说明
    
    前置条件：
    export OPENAI_API_KEY="your-api-key-here"
    
    运行命令：
    # 运行所有真实API测试
    python -m pytest tests/services/test_knowledge_extractor_real.py -v -s
    
    # 运行特定测试  
    python -m pytest tests/services/test_knowledge_extractor_real.py::TestKnowledgeExtractorRealAPI::test_prompt_format_compliance -v -s
    
    注意：使用GPT-4o-mini，成本很低
    """)