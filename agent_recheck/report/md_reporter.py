"""Markdown 报告生成器"""

from datetime import datetime
from pathlib import Path
from typing import Union

from models.report import AnalysisReport
from utils.logging import get_logger

logger = get_logger("report.md")


class MarkdownReporter:
    """Markdown 报告生成器"""

    def save(self, report: AnalysisReport, output: Union[str, Path]):
        """
        保存报告为 Markdown

        Args:
            report: 分析报告
            output: 输出路径
        """
        output = Path(output)

        content = self._generate_content(report)

        with open(output, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("markdown_report_saved", output=str(output))

    def _generate_content(self, report: AnalysisReport) -> str:
        """生成 Markdown 内容"""
        lines = []

        # 标题
        lines.append(f"# 政府采购招标文件合规性审查报告")
        lines.append("")
        lines.append(f"**文件**: {report.metadata.file_name}")
        lines.append(f"**审查时间**: {report.metadata.analyzed_at}")
        lines.append("")

        # 摘要
        lines.append("## 审查结果摘要")
        lines.append("")
        lines.append(f"| 风险等级 | 数量 |")
        lines.append(f"|----------|------|")
        lines.append(f"| 🔴 严重 | {report.summary.critical} |")
        lines.append(f"| 🟠 高风险 | {report.summary.high} |")
        lines.append(f"| 🟡 中风险 | {report.summary.medium} |")
        lines.append(f"| 🟢 低风险 | {report.summary.low} |")
        lines.append("")
        lines.append(f"**总计发现 {report.summary.total_issues} 个风险点**")
        lines.append("")

        # 详细问题
        if report.issues:
            lines.append("## 风险点详情")
            lines.append("")

            for i, issue in enumerate(report.issues, 1):
                lines.append(f"### {i}. {issue.title}")
                lines.append("")
                lines.append(f"**类别**: {issue.category}")
                lines.append(f"**风险等级**: {issue.level}")
                lines.append(f"**来源**: {issue.source}")
                lines.append("")
                lines.append("**原文引用**:")
                lines.append(f"```")
                lines.append(f"{issue.evidence.quote}")
                lines.append("```")
                lines.append("")
                lines.append(f"**法规依据**: {issue.rule.reference}")
                lines.append("")
                lines.append(f"**修改建议**: {issue.suggestion.content}")
                lines.append("")

                if issue.confidence < 1.0:
                    lines.append(f"**置信度**: {issue.confidence:.0%}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # 页脚
        lines.append("## 元信息")
        lines.append("")
        lines.append(f"- 知识库版本: {report.metadata.knowledge_base_version}")
        lines.append(f"- 规则版本: {report.metadata.rules_version}")
        lines.append(f"- 分析模式: {report.metadata.analysis_mode}")
        lines.append(f"- 分析耗时: {report.metadata.analysis_duration_ms}ms")

        return "\n".join(lines)
