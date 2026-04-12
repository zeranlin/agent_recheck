"""HTML 报告生成器"""

from pathlib import Path
from typing import Union

from ..models.report import AnalysisReport
from ..utils.logging import get_logger

logger = get_logger("report.html")


class HtmlReporter:
    """HTML 报告生成器"""

    def save(self, report: AnalysisReport, output: Union[str, Path]):
        """
        保存报告为 HTML

        Args:
            report: 分析报告
            output: 输出路径
        """
        output = Path(output)

        content = self._generate_html(report)

        with open(output, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("html_report_saved", output=str(output))

    def _generate_html(self, report: AnalysisReport) -> str:
        """生成 HTML 内容"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>合规性审查报告 - {report.metadata.file_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 1.8em; margin-bottom: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .summary-card .count {{ font-size: 2em; font-weight: bold; }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #28a745; }}
        .issues {{ background: white; border-radius: 8px; padding: 20px; margin-top: 20px; }}
        .issue {{ border-left: 4px solid #667eea; padding: 15px; margin-bottom: 15px; background: #f8f9fa; border-radius: 4px; }}
        .issue-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .issue-title {{ font-weight: bold; font-size: 1.1em; }}
        .badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.85em; }}
        .badge-critical {{ background: #dc3545; color: white; }}
        .badge-high {{ background: #fd7e14; color: white; }}
        .badge-medium {{ background: #ffc107; color: #333; }}
        .badge-low {{ background: #28a745; color: white; }}
        .quote {{ background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; font-family: monospace; }}
        .suggestion {{ background: #d4edda; padding: 10px; border-radius: 4px; margin-top: 10px; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 政府采购招标文件合规性审查报告</h1>
            <p>文件: {report.metadata.file_name}</p>
            <p>审查时间: {report.metadata.analyzed_at}</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <div class="count critical">{report.summary.critical}</div>
                <div>严重</div>
            </div>
            <div class="summary-card">
                <div class="count high">{report.summary.high}</div>
                <div>高风险</div>
            </div>
            <div class="summary-card">
                <div class="count medium">{report.summary.medium}</div>
                <div>中风险</div>
            </div>
            <div class="summary-card">
                <div class="count low">{report.summary.low}</div>
                <div>低风险</div>
            </div>
        </div>

        <div class="issues">
            <h2>风险点详情 (共 {report.summary.total_issues} 个)</h2>
            {self._generate_issues_html(report.issues)}
        </div>

        <div class="footer">
            <p>知识库版本: {report.metadata.knowledge_base_version} | 规则版本: {report.metadata.rules_version}</p>
            <p>分析耗时: {report.metadata.analysis_duration_ms}ms</p>
        </div>
    </div>
</body>
</html>
"""

    def _generate_issues_html(self, issues: list) -> str:
        """生成问题列表 HTML"""
        if not issues:
            return "<p>未发现风险点 ✅</p>"

        html_parts = []
        for issue in issues:
            badge_class = f"badge-{issue.level}"
            html_parts.append(f"""
            <div class="issue">
                <div class="issue-header">
                    <span class="issue-title">{issue.title}</span>
                    <span class="badge {badge_class}">{issue.level.upper()}</span>
                </div>
                <p><strong>类别:</strong> {issue.category}</p>
                <p><strong>来源:</strong> {issue.source}</p>
                <div class="quote">
                    <strong>原文引用:</strong><br>
                    {issue.evidence.quote}
                </div>
                <p><strong>法规依据:</strong> {issue.rule.reference}</p>
                <div class="suggestion">
                    <strong>修改建议:</strong><br>
                    {issue.suggestion.content}
                </div>
            </div>
            """)

        return "\n".join(html_parts)
