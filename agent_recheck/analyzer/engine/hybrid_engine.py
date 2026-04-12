"""混合分析引擎"""

from typing import Optional

from models.document import Document
from models.report import AnalysisReport, ReportSummary
from models.issue import Issue, IssueLocation, IssueEvidence, IssueRule, IssueSuggestion
from utils.logging import get_logger

from .rule_loader import RuleLoader
from .matcher import RuleMatcher
from .rule_manager import RuleManager
from ..llm.client import LLMClient
from ..llm.fallback import LLMFallback

logger = get_logger("engine.hybrid")


class HybridAnalysisEngine:
    """
    混合分析引擎

    支持三种模式：
    1. hybrid: 规则引擎 + LLM（默认）
    2. rules_only: 仅使用规则引擎
    3. llm_only: 仅使用 LLM
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

        # 初始化组件
        self.rule_loader = RuleLoader()
        self.rule_matcher = RuleMatcher()
        self.rule_manager = RuleManager()
        self.llm_client = LLMClient(config)
        self.llm_fallback = LLMFallback()

        # 加载规则
        self.rules = self.rule_loader.load_all()
        logger.info("hybrid_engine_initialized", rules_count=len(self.rules))

    def analyze(self, document: Document, mode: str = "hybrid") -> AnalysisReport:
        """
        分析文档

        Args:
            document: 文档对象
            mode: 分析模式 (hybrid / rules_only / llm_only)

        Returns:
            分析报告
        """
        logger.info("analysis_started", mode=mode, file=document.metadata.file_name)

        # 初始化报告
        report = AnalysisReport(
            summary=ReportSummary(),
            issues=[],
            metadata=document.metadata.__dict__,
        )

        try:
            if mode == "rules_only":
                issues = self._analyze_with_rules(document)
            elif mode == "llm_only":
                issues = self._analyze_with_llm(document)
            else:  # hybrid
                issues = self._analyze_hybrid(document)

            # 添加问题
            for issue in issues:
                report.add_issue(issue)

            logger.info(
                "analysis_completed",
                mode=mode,
                issues_found=len(issues),
            )

        except Exception as e:
            logger.error("analysis_error", error=str(e))
            # 降级到纯规则模式
            if mode == "hybrid":
                logger.warning("falling_back_to_rules")
                issues = self._analyze_with_rules(document)
                for issue in issues:
                    report.add_issue(issue)

        return report

    def _analyze_with_rules(self, document: Document) -> list[Issue]:
        """纯规则分析"""
        issues = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            result = self.rule_matcher.match(rule, document)

            if result.matched:
                issue = self._create_issue_from_match(document, result)
                issues.append(issue)

        return issues

    def _analyze_with_llm(self, document: Document) -> list[Issue]:
        """纯 LLM 分析"""
        try:
            if not self.llm_client.is_available():
                logger.warning("llm_unavailable")
                return []

            return self.llm_client.analyze(document)

        except Exception as e:
            logger.error("llm_analysis_failed", error=str(e))
            return self.llm_fallback.handle_failure(e, document)

    def _analyze_hybrid(self, document: Document) -> list[Issue]:
        """混合分析：规则引擎 + LLM"""
        issues = []

        # 1. 规则引擎快速扫描
        rule_issues = self._analyze_with_rules(document)
        issues.extend(rule_issues)

        # 2. LLM 深度分析
        try:
            if self.llm_client.is_available():
                llm_issues = self._analyze_with_llm(document)

                # 3. 交叉验证
                validated_issues = self._cross_validate(rule_issues, llm_issues)
                issues.extend(validated_issues)
            else:
                logger.warning("llm_unavailable_in_hybrid_mode")

        except Exception as e:
            logger.error("llm_analysis_failed_in_hybrid", error=str(e))
            # LLM 失败不影响规则分析结果

        # 4. 去重
        issues = self._deduplicate_issues(issues)

        return issues

    def _cross_validate(self, rule_issues: list[Issue], llm_issues: list[Issue]) -> list[Issue]:
        """交叉验证"""
        validated = []

        for llm_issue in llm_issues:
            # 检查是否有规则也发现了同样的问题
            found_by_rule = False

            for rule_issue in rule_issues:
                if self._issues_similar(llm_issue, rule_issue):
                    found_by_rule = True
                    # 规则确认，提升置信度
                    llm_issue.confidence = min(1.0, llm_issue.confidence + 0.2)
                    break

            # 如果 LLM 发现的规则未覆盖，增加其权重
            if not found_by_rule:
                llm_issue.confidence = llm_issue.confidence * 0.8  # 降低置信度

            validated.append(llm_issue)

        return validated

    def _issues_similar(self, issue1: Issue, issue2: Issue) -> bool:
        """判断两个问题是否相似"""
        # 基于文本相似度
        text1 = issue1.evidence.quote.lower()
        text2 = issue2.evidence.quote.lower()

        # 简单检查：是否有共同的关键词
        words1 = set(text1) - set("，。！？、：；""''（）")
        words2 = set(text2) - set("，。！？、：；""''（）")

        overlap = len(words1 & words2)
        return overlap >= 10

    def _deduplicate_issues(self, issues: list[Issue]) -> list[Issue]:
        """去重"""
        seen = set()
        unique = []

        for issue in issues:
            key = f"{issue.category}_{issue.evidence.highlight}_{issue.level}"
            if key not in seen:
                seen.add(key)
                unique.append(issue)

        return unique

    def _create_issue_from_match(self, document: Document, result) -> Issue:
        """从匹配结果创建问题"""
        location = IssueLocation(
            line_start=result.location.get("line", 0) if result.location else 0,
            line_end=result.location.get("line", 0) if result.location else 0,
        )

        evidence = IssueEvidence(
            quote=result.matched_text or "",
            location=location,
        )

        rule_info = IssueRule(
            id=result.rule.id,
            name=result.rule.name,
            reference=f"{result.rule.reference.law} {result.rule.reference.article}",
        )

        suggestion = IssueSuggestion(
            content=result.rule.suggestion.template,
        )

        return Issue(
            id=f"{result.rule.id}_{location.line_start}",
            type="规则匹配",
            category=result.rule.category.value if hasattr(result.rule.category, 'value') else result.rule.category,
            level=result.rule.level.value if hasattr(result.rule.level, 'value') else result.rule.level,
            title=result.rule.name,
            evidence=evidence,
            rule=rule_info,
            suggestion=suggestion,
            confidence=result.confidence,
            source="rule",
        )
