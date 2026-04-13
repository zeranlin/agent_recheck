"""analyze 命令实现"""

import json
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent_recheck.analyzer.engine.hybrid_engine import HybridAnalysisEngine, AnalysisResult
from agent_recheck.analyzer.parser.base import ParserFactory
from agent_recheck.models.report import AnalysisReport
from agent_recheck.report.json_reporter import JsonReporter
from agent_recheck.report.md_reporter import MarkdownReporter
from agent_recheck.report.html_reporter import HtmlReporter
from agent_recheck.utils.logging import get_logger

logger = get_logger("cli.analyze")
console = Console()


def analyze_command(
    file: Path,
    output: Optional[Path],
    format: str = "json",
    no_llm: bool = False,
    llm_only: bool = False,
    threshold: float = 0.7,
):
    """分析单个文件"""
    start_time = time.time()

    console.print(f"[bold]正在分析文件:[/bold] {file.name}")

    try:
        # 1. 解析文档
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("解析文档...", total=None)
            parser = ParserFactory.create_parser(file)
            document = parser.parse(file)
            progress.update(task, completed=True)

        logger.info("document_parsed", file=str(file), paragraphs=document.metadata.paragraph_count)

        # 2. 分析文档
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("审查合规性...", total=None)
            engine = HybridAnalysisEngine()

            analysis_mode = "llm_only" if llm_only else ("rules_only" if no_llm else "hybrid")
            result = engine.analyze(document, mode=analysis_mode)
            progress.update(task, completed=True)

        # 3. 处理结果
        analysis_duration_ms = int((time.time() - start_time) * 1000)

        if output:
            # 将 AnalysisResult 转换为兼容格式
            report_data = _convert_to_report(result, file, analysis_duration_ms)
            _save_report_data(report_data, output, format)
            console.print(f"[green]✓[/green] 报告已保存: {output}")
        else:
            _print_summary(result)

        logger.info(
            "analysis_completed",
            file=str(file),
            issues_found=result.summary()["total"],
            duration_ms=analysis_duration_ms,
        )

    except Exception as e:
        logger.error("analysis_failed", error=str(e), file=str(file))
        console.print(f"[red]✗[/red] 分析失败: {e}")
        raise typer.Exit(code=1)


def _convert_to_report(result: AnalysisResult, file: Path, duration_ms: int) -> dict:
    """将 AnalysisResult 转换为报告数据字典"""
    summary = result.summary()
    
    # 安全获取issue属性
    def safe_get_issue_data(issue, idx):
        level = getattr(issue, 'level', None)
        level_str = level.value if hasattr(level, 'value') else str(level) if level else 'medium'
        
        evidence = getattr(issue, 'evidence', None) or []
        evidence_data = []
        for e in evidence:
            evidence_data.append({
                "text": getattr(e, 'text', ''),
                "type": getattr(e, 'type', ''),
                "confidence": getattr(e, 'confidence', 0.0),
            })
        
        location = getattr(issue, 'location', None) or {}
        location_data = {
            "page": getattr(location, 'page', 0),
            "line": getattr(location, 'line', 0),
            "section": getattr(location, 'section', ''),
        }
        
        return {
            "id": f"issue_{idx}",
            "level": level_str,
            "category": getattr(issue, 'category', '其他'),
            "title": getattr(issue, 'title', '发现问题'),
            "description": getattr(issue, 'description', ''),
            "evidence": evidence_data,
            "location": location_data,
            "suggestion": getattr(issue, 'suggestion', '') if not hasattr(issue, 'suggestion') or not issue.suggestion else getattr(issue.suggestion, 'suggested', ''),
            "confidence": getattr(issue, 'confidence', 0.7),
            "source": getattr(issue, 'source', 'llm'),
        }
    
    return {
        "report_id": "",
        "document_name": file.name,
        "document_path": str(file),
        "created_at": "",
        "metadata": {
            "analysis_duration_ms": duration_ms,
            "mode": result.mode,
            "execution_time": result.execution_time,
        },
        "summary": {
            "total_issues": summary["total"],
            "critical": 0,
            "high_risk": summary["high"],
            "medium_risk": summary["medium"],
            "low_risk": summary["low"],
            "by_category": {},
            "by_severity": summary["by_source"],
        },
        "issues": [safe_get_issue_data(issue, i) for i, issue in enumerate(result.issues)],
        "warnings": result.warnings,
    }


def _save_report_data(report_data: dict, output: Path, format: str):
    """保存报告数据"""
    if format == "json":
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    elif format == "markdown":
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f"# 审查报告\n\n")
            f.write(f"## 文档信息\n\n")
            f.write(f"- 文件名: {report_data['document_name']}\n")
            f.write(f"- 路径: {report_data['document_path']}\n\n")
            f.write(f"## 摘要\n\n")
            summary = report_data['summary']
            f.write(f"- 总风险点: {summary['total_issues']}\n")
            f.write(f"- 高风险: {summary['high_risk']}\n")
            f.write(f"- 中风险: {summary['medium_risk']}\n")
            f.write(f"- 低风险: {summary['low_risk']}\n\n")
            if report_data['issues']:
                f.write(f"## 风险详情\n\n")
                for issue in report_data['issues']:
                    f.write(f"### {issue['title']}\n\n")
                    f.write(f"- 等级: {issue['level']}\n")
                    f.write(f"- 类别: {issue['category']}\n")
                    f.write(f"- 描述: {issue['description']}\n\n")
    else:
        raise ValueError(f"不支持的格式: {format}")


def _print_summary(result: AnalysisResult):
    """打印摘要"""
    from rich.table import Table

    summary = result.summary()

    table = Table(title="审查结果摘要")
    table.add_column("风险等级", style="bold")
    table.add_column("数量", justify="right")

    table.add_row("🔴 严重 (Critical)", "0", style="red")
    table.add_row("🟠 高风险 (High)", str(summary.get("high", 0)), style="bold red")
    table.add_row("🟡 中风险 (Medium)", str(summary.get("medium", 0)), style="yellow")
    table.add_row("🟢 低风险 (Low)", str(summary.get("low", 0)), style="green")

    console.print(table)

    total = summary.get("total", 0)
    if total > 0:
        console.print(f"\n发现 [bold]{total}[/bold] 个风险点")
    else:
        console.print("\n[green]✓ 未发现风险点[/green]")


# 导入 typer 以在异常时使用
import typer
