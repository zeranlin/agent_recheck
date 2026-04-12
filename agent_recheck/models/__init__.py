# -*- coding: utf-8 -*-
"""
数据模型模块

包含所有核心数据结构
"""

from .document import (
    Document,
    DocumentMetadata,
    DocumentSection,
    TableInfo,
    MarkedContent,
    ParsedDocument,
    ParsedSection,
    ParsedParagraph,
)
from .issue import (
    Issue,
    IssueLevel,
    IssueEvidence,
    IssueLocation,
    IssueRule,
    IssueSuggestion,
)
from .report import (
    Report,
    ReportSummary,
    ReportMetadata,
    AnalysisReport,
)
from .rule import (
    Rule,
    RuleCategory,
    RiskLevel,
    PatternMatch,
    RuleReference,
    RuleSuggestion,
)

__all__ = [
    # Document
    "Document",
    "DocumentMetadata",
    "DocumentSection",
    "TableInfo",
    "MarkedContent",
    "ParsedDocument",
    "ParsedSection",
    "ParsedParagraph",
    # Issue
    "Issue",
    "IssueLevel",
    "IssueEvidence",
    "IssueLocation",
    "IssueRule",
    "IssueSuggestion",
    # Report
    "Report",
    "ReportSummary",
    "ReportMetadata",
    "AnalysisReport",
    # Rule
    "Rule",
    "RuleCategory",
    "RiskLevel",
    "PatternMatch",
    "RuleReference",
    "RuleSuggestion",
]
