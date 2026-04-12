# -*- coding: utf-8 -*-
"""
报告数据模型
"""

from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime

from .issue import Issue


@dataclass
class ReportMetadata:
    """报告元数据"""
    report_id: str = ""
    document_name: str = ""
    document_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    total_pages: int = 0
    analysis_time: float = 0.0
    llm_calls: int = 0
    rules_evaluated: int = 0


@dataclass
class ReportSummary:
    """报告摘要"""
    total_issues: int = 0
    high_risk: int = 0
    medium_risk: int = 0
    low_risk: int = 0
    by_category: dict = field(default_factory=dict)
    by_severity: dict = field(default_factory=dict)


@dataclass
class Report:
    """审查报告"""
    metadata: ReportMetadata = field(default_factory=ReportMetadata)
    summary: ReportSummary = field(default_factory=ReportSummary)
    issues: List[Issue] = field(default_factory=list)
    consistency_issues: List[Any] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """分析报告（兼容名称）"""
    report_id: str = ""
    document_name: str = ""
    document_path: str = ""
    summary: ReportSummary = field(default_factory=ReportSummary)
    issues: List[Issue] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
