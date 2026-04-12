# -*- coding: utf-8 -*-
"""
报告构建器

统一的报告生成接口，支持多种输出格式：
- JSON: 结构化数据
- Markdown: 人类可读文档
- HTML: 可视化报告
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from models.issue import Issue
from models.report import Report, ReportSummary, ReportMetadata


@dataclass
class ReportConfig:
    """报告配置"""
    format: str = "markdown"           # 输出格式: json, markdown, html
    include_summary: bool = True       # 包含摘要
    include_details: bool = True       # 包含详细信息
    include_recommendations: bool = True  # 包含建议
    max_issues: int = 100              # 最大问题数
    group_by: str = "category"         # 分组方式: category, level, section


class ReportBuilder:
    """
    报告构建器
    
    统一接口生成各种格式的报告
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
    
    def build(
        self,
        issues: List[Issue],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Report:
        """
        构建报告
        
        Args:
            issues: 发现的问题列表
            metadata: 文档元数据
            
        Returns:
            Report 对象
        """
        # 构建摘要
        summary = self._build_summary(issues)
        
        # 构建问题分组
        grouped_issues = self._group_issues(issues)
        
        # 构建元数据
        report_metadata = ReportMetadata(
            generated_at=datetime.now(),
            document_title=metadata.get("title") if metadata else None,
            document_path=metadata.get("path") if metadata else None,
            analyzer_version=metadata.get("version", "1.0.0") if metadata else "1.0.0",
            analysis_mode=metadata.get("mode", "unknown") if metadata else "unknown",
        )
        
        return Report(
            metadata=report_metadata,
            summary=summary,
            issues=issues[:self.config.max_issues],
            grouped_issues=grouped_issues,
        )
    
    def _build_summary(self, issues: List[Issue]) -> ReportSummary:
        """构建摘要"""
        total = len(issues)
        by_level = {"high": 0, "medium": 0, "low": 0}
        by_category = {}
        
        for issue in issues:
            # 按级别统计
            level = issue.level.lower() if issue.level else "low"
            if level in by_level:
                by_level[level] += 1
            
            # 按类别统计
            category = issue.category or "other"
            by_category[category] = by_category.get(category, 0) + 1
        
        # 判断总体评价
        if by_level["high"] > 0:
            overall = "不合格"
        elif by_level["medium"] > 2:
            overall = "基本合格"
        else:
            overall = "合格"
        
        return ReportSummary(
            total_issues=total,
            high_risk=by_level["high"],
            medium_risk=by_level["medium"],
            low_risk=by_level["low"],
            by_category=by_category,
            overall=overall,
        )
    
    def _group_issues(
        self,
        issues: List[Issue],
    ) -> Dict[str, List[Issue]]:
        """分组问题"""
        grouped = {}
        
        for issue in issues:
            if self.config.group_by == "level":
                key = issue.level or "unknown"
            elif self.config.group_by == "category":
                key = issue.category or "other"
            else:
                key = "all"
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(issue)
        
        return grouped
    
    def to_json(self, report: Report) -> str:
        """导出为 JSON"""
        data = {
            "metadata": {
                "generated_at": report.metadata.generated_at.isoformat(),
                "document_title": report.metadata.document_title,
                "document_path": report.metadata.document_path,
                "analyzer_version": report.metadata.analyzer_version,
                "analysis_mode": report.metadata.analysis_mode,
            },
            "summary": {
                "total_issues": report.summary.total_issues,
                "high_risk": report.summary.high_risk,
                "medium_risk": report.summary.medium_risk,
                "low_risk": report.summary.low_risk,
                "by_category": report.summary.by_category,
                "overall": report.summary.overall,
            },
            "issues": [
                self._issue_to_dict(issue) for issue in report.issues
            ],
            "grouped_issues": {
                key: [self._issue_to_dict(i) for i in issues]
                for key, issues in report.grouped_issues.items()
            },
        }
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _issue_to_dict(self, issue: Issue) -> Dict[str, Any]:
        """将 Issue 转换为字典"""
        return {
            "id": issue.id,
            "type": issue.type,
            "category": issue.category,
            "level": issue.level,
            "title": issue.title,
            "evidence": issue.evidence.to_dict() if issue.evidence else None,
            "rule": issue.rule.to_dict() if issue.rule else None,
            "suggestion": issue.suggestion.to_dict() if issue.suggestion else None,
            "confidence": issue.confidence,
            "source": issue.source,
        }
    
    def to_markdown(self, report: Report) -> str:
        """导出为 Markdown"""
        lines = []
        
        # 标题
        lines.append(f"# 政府采购招投标文件合规性审查报告\n")
        
        # 元数据
        lines.append(f"**生成时间**: {report.metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        if report.metadata.document_title:
            lines.append(f"**文档名称**: {report.metadata.document_title}\n")
        if report.metadata.document_path:
            lines.append(f"**文档路径**: `{report.metadata.document_path}`\n")
        lines.append(f"**分析模式**: {report.metadata.analysis_mode}\n")
        lines.append(f"**版本**: {report.metadata.analyzer_version}\n")
        lines.append("\n---\n")
        
        # 摘要
        lines.append("## 审查摘要\n")
        lines.append(f"**总体评价**: {report.summary.overall}\n")
        lines.append(f"**问题总数**: {report.summary.total_issues}\n")
        lines.append(f"- 🔴 高风险: {report.summary.high_risk}\n")
        lines.append(f"- 🟡 中风险: {report.summary.medium_risk}\n")
        lines.append(f"- 🟢 低风险: {report.summary.low_risk}\n")
        
        if report.summary.by_category:
            lines.append("\n**按类别统计**:\n")
            for category, count in sorted(report.summary.by_category.items(), key=lambda x: -x[1]):
                lines.append(f"- {category}: {count}\n")
        
        lines.append("\n---\n")
        
        # 问题列表
        if report.issues:
            lines.append("## 问题详情\n")
            
            for issue in report.issues:
                # 问题标题
                level_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.level, "⚪")
                lines.append(f"### {level_icon} {issue.title}\n")
                
                lines.append(f"- **级别**: {issue.level or 'unknown'}\n")
                lines.append(f"- **类别**: {issue.category or 'other'}\n")
                lines.append(f"- **类型**: {issue.type}\n")
                lines.append(f"- **来源**: {issue.source}\n")
                lines.append(f"- **置信度**: {issue.confidence:.0%}\n")
                
                # 证据
                if issue.evidence and issue.evidence.quote:
                    lines.append(f"\n**原文引用**:\n")
                    lines.append(f"```\n{issue.evidence.quote}\n```\n")
                
                # 建议
                if issue.suggestion and issue.suggestion.content:
                    lines.append(f"\n**修改建议**:\n")
                    lines.append(f"{issue.suggestion.content}\n")
                
                # 法规依据
                if issue.rule and issue.rule.reference:
                    lines.append(f"\n**法规依据**:\n")
                    lines.append(f"{issue.rule.reference}\n")
                
                lines.append("\n---\n")
        
        return "".join(lines)
    
    def to_html(self, report: Report) -> str:
        """导出为 HTML"""
        template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>合规性审查报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .summary {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .summary-item {{
            text-align: center;
        }}
        .summary-value {{
            font-size: 2em;
            font-weight: bold;
        }}
        .summary-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .high {{ color: #dc3545; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #28a745; }}
        .overall {{
            text-align: center;
            padding: 10px;
            border-radius: 4px;
            margin-top: 15px;
        }}
        .overall.fail {{ background: #f8d7da; color: #721c24; }}
        .overall.warn {{ background: #fff3cd; color: #856404; }}
        .overall.pass {{ background: #d4edda; color: #155724; }}
        .issue {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .issue-header {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .issue-title {{
            font-size: 1.1em;
            font-weight: bold;
            margin-left: 10px;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-right: 5px;
        }}
        .badge-high {{ background: #f8d7da; color: #721c24; }}
        .badge-medium {{ background: #fff3cd; color: #856404; }}
        .badge-low {{ background: #d4edda; color: #155724; }}
        .evidence {{
            background: #f8f9fa;
            padding: 10px;
            border-left: 3px solid #007bff;
            margin: 10px 0;
            font-family: monospace;
            white-space: pre-wrap;
        }}
        .suggestion {{
            background: #e7f3ff;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }}
        .reference {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            color: #999;
            margin-top: 30px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏛️ 政府采购招投标文件合规性审查报告</h1>
        <p><strong>生成时间</strong>: {generated_at}</p>
        <p><strong>文档名称</strong>: {document_title}</p>
        <p><strong>分析模式</strong>: {analysis_mode}</p>
    </div>
    
    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-value">{total}</div>
                <div class="summary-label">问题总数</div>
            </div>
            <div class="summary-item">
                <div class="summary-value high">{high}</div>
                <div class="summary-label">高风险</div>
            </div>
            <div class="summary-item">
                <div class="summary-value medium">{medium}</div>
                <div class="summary-label">中风险</div>
            </div>
            <div class="summary-item">
                <div class="summary-value low">{low}</div>
                <div class="summary-label">低风险</div>
            </div>
        </div>
        <div class="overall {overall_class}">
            <strong>总体评价</strong>: {overall}
        </div>
    </div>
    
    {issues_html}
    
    <div class="footer">
        <p>由 agent_recheck 自动生成 | 版本 {version}</p>
    </div>
</body>
</html>
"""
        
        # 生成问题 HTML
        issues_html = ""
        for issue in report.issues[:self.config.max_issues]:
            badge_class = f"badge-{issue.level}" if issue.level else "badge-low"
            evidence_html = f'<div class="evidence">{issue.evidence.quote}</div>' if issue.evidence and issue.evidence.quote else ""
            suggestion_html = f'<div class="suggestion"><strong>建议</strong>: {issue.suggestion.content}</div>' if issue.suggestion and issue.suggestion.content else ""
            reference_html = f'<div class="reference"><strong>法规依据</strong>: {issue.rule.reference}</div>' if issue.rule and issue.rule.reference else ""
            
            issues_html += f"""
        <div class="issue">
            <div class="issue-header">
                <span class="badge {badge_class}">{issue.level or 'unknown'}</span>
                <span class="issue-title">{issue.title}</span>
            </div>
            <div>
                <span>类别: {issue.category or 'other'}</span> |
                <span>置信度: {issue.confidence:.0%}</span> |
                <span>来源: {issue.source}</span>
            </div>
            {evidence_html}
            {suggestion_html}
            {reference_html}
        </div>
            """
        
        # 确定 overall 样式
        overall_class = {"不合格": "fail", "基本合格": "warn", "合格": "pass"}.get(report.summary.overall, "pass")
        
        return template.format(
            generated_at=report.metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            document_title=report.metadata.document_title or "未知",
            analysis_mode=report.metadata.analysis_mode,
            total=report.summary.total_issues,
            high=report.summary.high_risk,
            medium=report.summary.medium_risk,
            low=report.summary.low_risk,
            overall=report.summary.overall,
            overall_class=overall_class,
            issues_html=issues_html,
            version=report.metadata.analyzer_version,
        )
    
    def save(self, report: Report, output_path: str) -> None:
        """保存报告到文件"""
        if self.config.format == "json":
            content = self.to_json(report)
        elif self.config.format == "html":
            content = self.to_html(report)
        else:
            content = self.to_markdown(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)


# 导出
__all__ = [
    'ReportBuilder',
    'ReportConfig',
]
