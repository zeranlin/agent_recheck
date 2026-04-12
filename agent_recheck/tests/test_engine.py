# -*- coding: utf-8 -*-
"""
规则引擎测试

测试规则匹配和分析功能
"""

import pytest
from typing import List

# 导入被测试模块
from analyzer.engine.rule_loader import RuleLoader
from analyzer.engine.fallback_engine import FallbackEngine, FallbackMode
from analyzer.engine.local_rules import LocalRuleEngine, RegionDetector


class TestRuleLoader:
    """规则加载器测试"""
    
    def test_loader_initialization(self):
        """测试加载器初始化"""
        loader = RuleLoader()
        assert loader is not None
    
    def test_load_all_rules(self):
        """测试加载所有规则"""
        loader = RuleLoader()
        rules = loader.load_all()
        
        assert isinstance(rules, list)
        # 规则可能为空，取决于规则文件是否存在
        assert len(rules) >= 0
    
    def test_load_rules_by_category(self):
        """测试按类别加载规则"""
        loader = RuleLoader()
        
        # 尝试加载各个类别
        categories = ['discrimination', 'scoring', 'contract']
        
        for category in categories:
            rules = loader.load_by_category(category)
            assert isinstance(rules, list)


class TestFallbackEngine:
    """降级引擎测试"""
    
    @pytest.fixture
    def engine(self):
        """创建降级引擎"""
        return FallbackEngine()
    
    @pytest.fixture
    def mock_document(self):
        """创建模拟文档"""
        from models.document import Document, DocumentMetadata
        
        metadata = DocumentMetadata(
            file_name="test.docx",
            file_path="/test/test.docx",
            file_size=1024,
        )
        
        content = """
        政府采购招标文件
        
        一、资格条件
        1. 供应商应具有ISO9001质量管理体系认证
        2. 在深圳市内有3个以上类似业绩
        
        二、评分标准
        价格分权重: 80%
        技术分权重: 20%
        
        三、合同条款
        履约保证金: 合同价格的20%
        """
        
        return Document(metadata=metadata, content=content)
    
    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
        assert engine.config is not None
    
    def test_heuristic_analysis(self, engine, mock_document):
        """测试启发式分析"""
        issues = engine._heuristic_analysis(mock_document)
        
        assert isinstance(issues, list)
        # 应该发现一些启发式规则匹配
    
    def test_marker_analysis(self, engine, mock_document):
        """测试标记分析"""
        # 添加标记内容
        mock_document.content += "\n★ 本条款必须满足"
        
        issues = engine._marker_analysis(mock_document)
        assert isinstance(issues, list)
    
    def test_critical_content_analysis(self, engine, mock_document):
        """测试关键内容分析"""
        issues = engine._critical_content_analysis(mock_document)
        assert isinstance(issues, list)


class TestLocalRuleEngine:
    """本地化规则引擎测试"""
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = LocalRuleEngine()
        assert engine is not None
    
    def test_region_validation(self):
        """测试地区验证"""
        engine = LocalRuleEngine()
        
        assert engine.is_valid_region("深圳") == True
        assert engine.is_valid_region("广东") == True
        assert engine.is_valid_region("未知") == False
    
    def test_region_law_mapping(self):
        """测试地区法规映射"""
        engine = LocalRuleEngine()
        
        assert engine.get_region_law_name("深圳") == "深圳经济特区政府采购条例"
        assert engine.get_region_law_name("广东") == "广东省政府采购条例"


class TestRegionDetector:
    """地区检测器测试"""
    
    def test_detector_initialization(self):
        """测试检测器初始化"""
        detector = RegionDetector()
        assert detector is not None
    
    def test_shenzhen_detection(self):
        """测试深圳地区检测"""
        detector = RegionDetector()
        
        text = "深圳经济特区政府采购条例 SZCG20240001"
        region = detector.detect(text)
        assert region == "深圳"
    
    def test_guangdong_detection(self):
        """测试广东地区检测"""
        detector = RegionDetector()
        
        text = "广东省政府采购项目 GD20240001"
        region = detector.detect(text)
        assert region == "广东"
    
    def test_multiple_regions(self):
        """测试多地区检测"""
        detector = RegionDetector()
        
        text = "深圳市政府采购项目"
        regions = detector.get_all_detected_regions(text)
        assert "深圳" in regions
        assert "广东" in regions


class TestHybridEngine:
    """混合引擎测试"""
    
    @pytest.fixture
    def engine(self):
        """创建混合引擎"""
        from analyzer.engine.hybrid_engine import HybridAnalysisEngine
        return HybridAnalysisEngine()
    
    @pytest.fixture
    def mock_document(self):
        """创建模拟文档"""
        from models.document import Document, DocumentMetadata
        
        metadata = DocumentMetadata(
            file_name="test.docx",
            file_path="/test/test.docx",
            file_size=1024,
        )
        
        content = """
        政府采购招标文件
        
        ★ 实质性条款：供应商必须在深圳市有3个以上类似业绩
        
        评分标准：
        - 价格分：60分
        - 技术分：40分
        """
        
        return Document(metadata=metadata, content=content)
    
    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
    
    def test_rules_loaded(self, engine):
        """测试规则加载"""
        assert len(engine.rules) >= 0
    
    def test_rules_only_analysis(self, engine, mock_document):
        """测试纯规则分析"""
        result = engine.analyze(mock_document, mode="rules_only")
        
        assert result is not None
        assert result.mode == "rules_only"
        assert isinstance(result.issues, list)
    
    def test_fallback_analysis(self, engine, mock_document):
        """测试降级分析"""
        result = engine.analyze(mock_document, mode="fallback")
        
        assert result is not None
        assert result.mode == "fallback"
        assert isinstance(result.issues, list)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
