# -*- coding: utf-8 -*-
"""
端到端集成测试

测试完整的审查流程
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch

from ..analyzer.workflow import ReviewWorkflow, ReviewConfig, BatchReviewWorkflow
from ..analyzer.engine.rule_loader import RuleLoader
from ..analyzer.engine.hybrid_engine import HybridEngine
from ..analyzer.parser.base import ParsedDocument, ParsedSection, ParsedParagraph
from ..analyzer.engine.matcher import MatchResult
from ..report.report_builder import ReportBuilder


class TestReviewWorkflow:
    """审查工作流测试"""

    def test_create_task(self):
        """测试创建任务"""
        workflow = ReviewWorkflow()
        task = workflow.create_task("/path/to/document.docx", "测试文档")

        assert task is not None
        assert task.document_path == "/path/to/document.docx"
        assert task.document_name == "测试文档"
        assert task.status.value == "pending"

    def test_config_defaults(self):
        """测试默认配置"""
        config = ReviewConfig()
        assert config.enable_llm is True
        assert config.enable_consistency is True
        assert config.enable_local_rules is True
        assert config.max_llm_calls == 50
        assert config.confidence_threshold == 0.7

    @patch("agent_recheck.analyzer.workflow.ReviewWorkflow._parse_document")
    def test_execute_task_parsing(self, mock_parse):
        """测试任务执行-解析阶段"""
        mock_doc = Mock(spec=ParsedDocument)
        mock_doc.metadata = {"page_count": 10}
        mock_doc.tables = []
        mock_doc.sections = []
        mock_doc.paragraphs = []
        mock_parse.return_value = mock_doc

        workflow = ReviewWorkflow(ReviewConfig(enable_llm=False, enable_consistency=False))
        task = workflow.create_task("/path/to/test.docx")

        with patch.object(workflow, "_run_rule_matching") as mock_rules:
            mock_result = Mock(spec=MatchResult)
            mock_result.issues = []
            mock_rules.return_value = mock_result

            result = workflow.execute_task(task)

        assert task.status.value == "completed"
        assert "parsing" in task.stages
        assert task.stages["parsing"]["status"] == "completed"


class TestBatchReviewWorkflow:
    """批量审查工作流测试"""

    def test_add_task(self):
        """测试添加任务"""
        workflow = BatchReviewWorkflow()
        task = workflow.add_task("/path/to/doc1.docx", "文档1")

        assert len(workflow.tasks) == 1
        assert task.document_name == "文档1"

    def test_add_multiple_tasks(self):
        """测试添加多个任务"""
        workflow = BatchReviewWorkflow()
        workflow.add_task("/path/to/doc1.docx", "文档1")
        workflow.add_task("/path/to/doc2.pdf", "文档2")
        workflow.add_task("/path/to/doc3.docx", "文档3")

        assert len(workflow.tasks) == 3

    def test_get_summary_empty(self):
        """测试空批次汇总"""
        workflow = BatchReviewWorkflow()
        summary = workflow.get_summary()

        assert summary["total_tasks"] == 0
        assert summary["completed"] == 0
        assert summary["failed"] == 0


class TestRuleLoader:
    """规则加载器测试"""

    def test_load_all_rules(self):
        """测试加载所有规则"""
        loader = RuleLoader()
        rules = loader.load_all_rules()

        assert isinstance(rules, list)
        for rule in rules:
            assert "id" in rule
            assert "name" in rule

    def test_load_rules_by_category(self):
        """测试按类别加载规则"""
        loader = RuleLoader()
        discrimination_rules = loader.load_rules_by_category("discrimination")

        for rule in discrimination_rules:
            assert rule.get("category") == "discrimination"

    def test_rule_structure(self):
        """测试规则结构"""
        loader = RuleLoader()
        rules = loader.load_all_rules()

        for rule in rules:
            assert "id" in rule
            assert "name" in rule
            assert "patterns" in rule
            assert "severity" in rule
            assert rule["severity"] in ["high", "medium", "low"]


class TestHybridEngine:
    """混合引擎测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = HybridEngine(llm_enabled=False)
        assert engine is not None
        assert engine.llm_enabled is False

    def test_fallback_mode(self):
        """测试降级模式"""
        engine = HybridEngine(llm_enabled=True, fallback_mode="hybrid")

        mock_doc = Mock(spec=ParsedDocument)
        mock_doc.metadata = {}
        mock_doc.sections = []
        mock_doc.paragraphs = []
        mock_doc.tables = []

        with patch.object(engine, "llm_client") as mock_llm:
            mock_llm.analyze.side_effect = Exception("LLM unavailable")

            result = engine.analyze(mock_doc)
            assert result is not None


class TestReportBuilder:
    """报告构建器测试"""

    def test_builder_initialization(self):
        """测试构建器初始化"""
        builder = ReportBuilder()
        assert builder is not None

    def test_config_initialization(self):
        """测试配置初始化"""
        config = ReportConfig(
            title="测试报告",
            include_summary=True,
            group_by="category"
        )
        assert config.title == "测试报告"
        assert config.include_summary is True

    def test_build_json_format(self):
        """测试JSON输出"""
        builder = ReportBuilder()
        mock_result = Mock()
        mock_result.issues = []
        mock_result.metadata = {"total_issues": 0}

        output = builder.build_json(mock_result, None, ReportConfig())
        assert output is not None
        assert "total_issues" in output

    def test_build_markdown_format(self):
        """测试Markdown输出"""
        builder = ReportBuilder()
        mock_result = Mock()
        mock_result.issues = []
        mock_result.metadata = {"total_issues": 0}

        output = builder.build_markdown(mock_result, None, ReportConfig(title="测试报告"))
        assert "# 测试报告" in output


class TestEndToEnd:
    """端到端测试"""

    def test_full_workflow_mock(self):
        """测试完整流程（模拟）"""
        workflow = ReviewWorkflow(ReviewConfig(
            enable_llm=False,
            enable_consistency=False
        ))

        mock_doc = Mock(spec=ParsedDocument)
        mock_doc.metadata = {"page_count": 5}
        mock_doc.tables = []
        mock_doc.sections = []
        mock_doc.paragraphs = []

        mock_result = Mock()
        mock_result.issues = []

        with patch.object(workflow, "_parse_document", return_value=mock_doc):
            with patch.object(workflow, "_run_rule_matching", return_value=mock_result):
                with patch.object(workflow, "_combine_results", return_value=mock_result):
                    with patch.object(workflow, "_generate_reports", return_value={"json": "{}"}):
                        task = workflow.create_task("/test/document.docx")
                        result = workflow.execute_task(task)

        assert result["status"] == "completed"
        assert "result" in result

    def test_error_handling(self):
        """测试错误处理"""
        workflow = ReviewWorkflow()

        with patch.object(workflow, "_parse_document", side_effect=ValueError("Invalid file")):
            task = workflow.create_task("/test/invalid.docx")
            with pytest.raises(ValueError):
                workflow.execute_task(task)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
