"""报告生成模块"""

from .json_reporter import JsonReporter
from .md_reporter import MarkdownReporter
from .html_reporter import HtmlReporter
from .report_builder import ReportBuilder, ReportConfig

__all__ = [
    # 独立报告器
    "JsonReporter",
    "MarkdownReporter",
    "HtmlReporter",
    # 统一报告构建器
    "ReportBuilder",
    "ReportConfig",
]
