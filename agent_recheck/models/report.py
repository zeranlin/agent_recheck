"""报告数据模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .issue import Issue


class ReportSummary(BaseModel):
    """报告摘要"""
    total_issues: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    by_category: dict[str, int] = {}
    by_source: dict[str, int] = {}  # rule, llm


class ReportMetadata(BaseModel):
    """报告元数据"""
    file_name: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    knowledge_base_version: str = "unknown"
    rules_version: str = "unknown"
    llm_model: Optional[str] = None
    analysis_mode: str = "hybrid"  # hybrid, rules_only, llm_only
    analysis_duration_ms: int = 0


class AnalysisReport(BaseModel):
    """分析报告模型"""
    summary: ReportSummary
    issues: list[Issue]
    metadata: ReportMetadata

    def add_issue(self, issue: Issue):
        """添加问题"""
        self.issues.append(issue)
        self._recalculate_summary()

    def _recalculate_summary(self):
        """重新计算摘要"""
        self.summary.total_issues = len(self.issues)
        self.summary.critical = sum(1 for i in self.issues if i.level == "critical")
        self.summary.high = sum(1 for i in self.issues if i.level == "high")
        self.summary.medium = sum(1 for i in self.issues if i.level == "medium")
        self.summary.low = sum(1 for i in self.issues if i.level == "low")

        # 按类别统计
        self.summary.by_category = {}
        for issue in self.issues:
            self.summary.by_category[issue.category] = \
                self.summary.by_category.get(issue.category, 0) + 1

        # 按来源统计
        self.summary.by_source = {}
        for issue in self.issues:
            self.summary.by_source[issue.source] = \
                self.summary.by_source.get(issue.source, 0) + 1

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
