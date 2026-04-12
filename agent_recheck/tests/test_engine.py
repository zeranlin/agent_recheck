"""规则引擎测试"""

import pytest
from models.rule import Rule, RuleCategory, RiskLevel, PatternMatch, RuleReference, RuleSuggestion
from models.document import Document, DocumentMetadata
from analyzer.engine.rule_loader import RuleLoader
from analyzer.engine.matcher import RuleMatcher


class TestRuleLoader:
    """规则加载器测试"""

    def test_load_rules_from_directory(self):
        """测试从目录加载规则"""
        loader = RuleLoader()
        rules = loader.load_all()

        assert isinstance(rules, list)
        # 如果有规则文件，应该能加载
        for rule in rules:
            assert isinstance(rule, Rule)
            assert rule.id is not None
            assert rule.name is not None


class TestRuleMatcher:
    """规则匹配器测试"""

    def test_keyword_match(self):
        """测试关键词匹配"""
        matcher = RuleMatcher()

        # 创建测试规则
        rule = Rule(
            id="TEST-001",
            name="测试规则",
            category=RuleCategory.DISCRIMINATION,
            level=RiskLevel.HIGH,
            pattern=PatternMatch(
                type="keyword",
                match=["北京", "上海"],
            ),
            reference=RuleReference(
                law="政府采购法",
                article="第二十条",
            ),
            suggestion=RuleSuggestion(
                template="删除地域限制",
            ),
        )

        # 创建测试文档
        doc = Document(
            metadata=DocumentMetadata(
                file_path="test.docx",
                file_name="test.docx",
                file_size=1000,
                file_type="docx",
            ),
            full_text="本项目要求供应商具有北京市政府采购业绩。",
        )

        result = matcher.match(rule, doc)

        assert result.matched is True
        assert result.matched_text is not None

    def test_regex_match(self):
        """测试正则匹配"""
        matcher = RuleMatcher()

        rule = Rule(
            id="TEST-002",
            name="测试规则",
            category=RuleCategory.DISCRIMINATION,
            level=RiskLevel.HIGH,
            pattern=PatternMatch(
                type="regex",
                match=[r".{0,10}业绩.{0,20}"],
            ),
            reference=RuleReference(
                law="政府采购法",
                article="第二十条",
            ),
            suggestion=RuleSuggestion(
                template="修改业绩要求",
            ),
        )

        doc = Document(
            metadata=DocumentMetadata(
                file_path="test.docx",
                file_name="test.docx",
                file_size=1000,
                file_type="docx",
            ),
            full_text="本项目要求供应商具有3年以上政府采购业绩。",
        )

        result = matcher.match(rule, doc)

        assert result.matched is True

    def test_no_match(self):
        """测试无匹配"""
        matcher = RuleMatcher()

        rule = Rule(
            id="TEST-003",
            name="测试规则",
            category=RuleCategory.DISCRIMINATION,
            level=RiskLevel.HIGH,
            pattern=PatternMatch(
                type="keyword",
                match=["北京"],
            ),
            reference=RuleReference(
                law="政府采购法",
                article="第二十条",
            ),
            suggestion=RuleSuggestion(
                template="删除地域限制",
            ),
        )

        doc = Document(
            metadata=DocumentMetadata(
                file_path="test.docx",
                file_name="test.docx",
                file_size=1000,
                file_type="docx",
            ),
            full_text="本项目欢迎全国各地供应商参与。",
        )

        result = matcher.match(rule, doc)

        assert result.matched is False
