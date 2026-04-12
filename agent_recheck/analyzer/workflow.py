# -*- coding: utf-8 -*-
"""
规则审核工作流

提供完整的审查流程管理：
1. 审查计划制定
2. 分阶段审查
3. 结果审核
4. 报告输出
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from .parser.base import ParsedDocument
from .engine.hybrid_engine import HybridAnalysisEngine as HybridEngine, AnalysisResult
from .engine.fallback_engine import FallbackEngine
from ..report.report_builder import ReportBuilder, ReportConfig


class ReviewStage(Enum):
    """审查阶段"""
    PLANNING = "planning"           # 计划制定
    DOCUMENT_PARSING = "parsing"    # 文档解析
    RULE_MATCHING = "matching"      # 规则匹配
    LLM_ANALYSIS = "llm_analysis"  # LLM分析
    CONSISTENCY_CHECK = "consistency"  # 一致性检查
    RESULT_REVIEW = "review"       # 结果审核
    REPORT_GENERATION = "report"   # 报告生成
    COMPLETED = "completed"        # 完成


class ReviewStatus(Enum):
    """审查状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ReviewTask:
    """审查任务"""
    task_id: str
    document_path: str
    document_name: str
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ReviewStatus = ReviewStatus.PENDING
    current_stage: ReviewStage = ReviewStage.PLANNING
    progress: float = 0.0  # 0.0 - 1.0
    stages: dict[str, dict] = field(default_factory=dict)
    result: Optional[AnalysisResult] = None
    consistency_result: Optional[Any] = None
    error: Optional[str] = None

    def update_stage(self, stage: ReviewStage, status: str, data: dict = None) -> None:
        """更新阶段状态"""
        stage_name = stage.value
        if stage_name not in self.stages:
            self.stages[stage_name] = {
                "status": status,
                "started_at": datetime.now().isoformat(),
                "data": data or {}
            }
        else:
            self.stages[stage_name]["status"] = status
            self.stages[stage_name]["data"] = data or {}

        self.current_stage = stage

        if status == "completed":
            self.stages[stage_name]["completed_at"] = datetime.now().isoformat()
            self._update_progress()

    def _update_progress(self) -> None:
        """更新总体进度"""
        stage_order = [s.value for s in ReviewStage]
        current_idx = stage_order.index(self.current_stage.value)
        self.progress = (current_idx + 1) / len(stage_order)


@dataclass
class ReviewConfig:
    """审查配置"""
    enable_llm: bool = True
    enable_consistency: bool = True
    enable_local_rules: bool = True
    max_llm_calls: int = 50
    confidence_threshold: float = 0.7
    output_formats: list[str] = field(default_factory=lambda: ["json", "markdown"])
    output_path: Optional[str] = None
    custom_rules: list[str] = field(default_factory=list)


class ReviewWorkflow:
    """审查工作流"""

    def __init__(self, config: ReviewConfig = None):
        self.config = config or ReviewConfig()
        self.hybrid_engine = None
        self.fallback_engine = FallbackEngine()
        self.report_builder = ReportBuilder()
        self.current_task: Optional[ReviewTask] = None

    def create_task(self, document_path: str, document_name: str = None) -> ReviewTask:
        """创建审查任务"""
        task = ReviewTask(
            task_id=self._generate_task_id(),
            document_path=document_path,
            document_name=document_name or document_path.split("/")[-1]
        )
        self.current_task = task
        return task

    def execute_task(self, task: ReviewTask) -> dict:
        """执行审查任务"""
        task.status = ReviewStatus.IN_PROGRESS
        task.started_at = datetime.now()

        try:
            # 阶段1: 文档解析
            task.update_stage(ReviewStage.DOCUMENT_PARSING, "in_progress")
            document = self._parse_document(task.document_path)
            task.update_stage(ReviewStage.DOCUMENT_PARSING, "completed", {
                "page_count": document.metadata.get("page_count", 0),
                "table_count": len(document.tables),
                "section_count": len(document.sections)
            })

            # 阶段2: 规则匹配
            task.update_stage(ReviewStage.RULE_MATCHING, "in_progress")
            rule_result = self._run_rule_matching(document)
            task.update_stage(ReviewStage.RULE_MATCHING, "completed", {
                "rule_count": len(rule_result.issues),
                "high_risk_count": sum(1 for i in rule_result.issues if i.severity.value == "high")
            })

            # 阶段3: LLM分析 (如果启用)
            if self.config.enable_llm:
                task.update_stage(ReviewStage.LLM_ANALYSIS, "in_progress")
                llm_result = self._run_llm_analysis(document)
                task.update_stage(ReviewStage.LLM_ANALYSIS, "completed", {
                    "llm_issues": len(llm_result.issues) if llm_result else 0
                })
            else:
                task.update_stage(ReviewStage.LLM_ANALYSIS, "skipped")

            # 阶段4: 一致性检查
            if self.config.enable_consistency:
                task.update_stage(ReviewStage.CONSISTENCY_CHECK, "in_progress")
                consistency_result = self._run_consistency_check(document)
                task.consistency_result = consistency_result
                task.update_stage(ReviewStage.CONSISTENCY_CHECK, "completed", {
                    "issue_count": len(consistency_result.issues),
                    "error_count": len(consistency_result.get_issues_by_severity(
                        __import__('agent_recheck.analyzer.consistency', fromlist=['Severity']).Severity.ERROR
                    ))
                })
            else:
                task.update_stage(ReviewStage.CONSISTENCY_CHECK, "skipped")

            # 阶段5: 结果合并
            task.update_stage(ReviewStage.RESULT_REVIEW, "in_progress")
            combined_result = self._combine_results(rule_result, llm_result)
            task.result = combined_result
            task.update_stage(ReviewStage.RESULT_REVIEW, "completed")

            # 阶段6: 报告生成
            task.update_stage(ReviewStage.REPORT_GENERATION, "in_progress")
            reports = self._generate_reports(task, combined_result, consistency_result)
            task.update_stage(ReviewStage.REPORT_GENERATION, "completed", reports)

            # 完成
            task.update_stage(ReviewStage.COMPLETED, "completed")
            task.status = ReviewStatus.COMPLETED
            task.completed_at = datetime.now()

            return {
                "task_id": task.task_id,
                "status": "completed",
                "result": combined_result,
                "consistency": consistency_result if self.config.enable_consistency else None,
                "reports": reports
            }

        except Exception as e:
            task.status = ReviewStatus.FAILED
            task.error = str(e)
            task.update_stage(task.current_stage, "failed", {"error": str(e)})
            raise

    def _parse_document(self, document_path: str) -> ParsedDocument:
        """解析文档"""
        from .parser.docx_parser import DocxParser
        from .parser.pdf_parser import PdfParser
        import os

        ext = os.path.splitext(document_path)[1].lower()

        if ext == ".docx":
            parser = DocxParser()
        elif ext == ".pdf":
            parser = PdfParser()
        else:
            raise ValueError(f"Unsupported document format: {ext}")

        return parser.parse(document_path)

    def _run_rule_matching(self, document: ParsedDocument) -> AnalysisResult:
        """运行规则匹配"""
        from .engine.rule_loader import RuleLoader
        from .engine.matcher import RuleMatcher

        rule_loader = RuleLoader()
        rules = rule_loader.load_all_rules()

        matcher = RuleMatcher(rules)
        return matcher.match_document(document)

    def _run_llm_analysis(self, document: ParsedDocument) -> Optional[AnalysisResult]:
        """运行LLM分析"""
        if not self.config.enable_llm:
            return None

        if self.hybrid_engine is None:
            self.hybrid_engine = HybridEngine(llm_enabled=True)

        try:
            return self.hybrid_engine.analyze(document)
        except Exception:
            return self.fallback_engine.analyze(document)

    def _run_consistency_check(self, document: ParsedDocument) -> Any:
        """运行一致性检查"""
        checker = ConsistencyChecker(document)
        return checker.check_all()

    def _combine_results(
        self,
        rule_result: AnalysisResult,
        llm_result: Optional[AnalysisResult]
    ) -> AnalysisResult:
        """合并结果"""
        from .aggregator.merger import IssueAggregator

        aggregator = IssueAggregator()
        combined = aggregator.combine_results([rule_result, llm_result])
        return combined

    def _generate_reports(
        self,
        task: ReviewTask,
        result: AnalysisResult,
        consistency: Any
    ) -> dict:
        """生成报告"""
        reports = {}

        config = ReportConfig(
            title=f"招标文件合规性审查报告 - {task.document_name}",
            include_summary=True,
            include_details=True,
            group_by="category"
        )

        for fmt in self.config.output_formats:
            if fmt == "json":
                reports["json"] = self.report_builder.build_json(result, consistency, config)
            elif fmt == "markdown":
                reports["markdown"] = self.report_builder.build_markdown(result, consistency, config)
            elif fmt == "html":
                reports["html"] = self.report_builder.build_html(result, consistency, config)

        if self.config.output_path:
            for fmt, content in reports.items():
                output_file = f"{self.config.output_path}/{task.task_id}.{fmt}"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)

        return reports

    def _generate_task_id(self) -> str:
        """生成任务ID"""
        import uuid
        return f"review_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

    def get_task_status(self, task_id: str) -> dict:
        """获取任务状态"""
        if self.current_task and self.current_task.task_id == task_id:
            return {
                "task_id": task_id,
                "status": self.current_task.status.value,
                "progress": self.current_task.progress,
                "current_stage": self.current_task.current_stage.value,
                "stages": self.current_task.stages
            }
        return {"error": "Task not found"}


class BatchReviewWorkflow(ReviewWorkflow):
    """批量审查工作流"""

    def __init__(self, config: ReviewConfig = None):
        super().__init__(config)
        self.tasks: list[ReviewTask] = []

    def add_task(self, document_path: str, document_name: str = None) -> ReviewTask:
        """添加审查任务"""
        task = self.create_task(document_path, document_name)
        self.tasks.append(task)
        return task

    def execute_all(self, max_parallel: int = 3) -> list[dict]:
        """执行所有任务"""
        results = []
        for task in self.tasks:
            try:
                result = self.execute_task(task)
                results.append(result)
            except Exception as e:
                results.append({
                    "task_id": task.task_id,
                    "status": "failed",
                    "error": str(e)
                })
        return results

    def get_summary(self) -> dict:
        """获取汇总结果"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.status == ReviewStatus.COMPLETED)
        failed = sum(1 for t in self.tasks if t.status == ReviewStatus.FAILED)

        total_issues = sum(
            len(t.result.issues) if t.result else 0
            for t in self.tasks if t.status == ReviewStatus.COMPLETED
        )

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "total_issues": total_issues,
            "average_progress": sum(t.progress for t in self.tasks) / total if total > 0 else 0
        }
