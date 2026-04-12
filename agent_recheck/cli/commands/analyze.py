"""analyze 命令实现"""

import json
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from analyzer.engine.hybrid_engine import HybridAnalysisEngine
from analyzer.parser.base import ParserFactory
from models.report import AnalysisReport
from report.json_reporter import JsonReporter
from report.md_reporter import MarkdownReporter
from report.html_reporter import HtmlReporter
from utils.logging import get_logger

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
            report = engine.analyze(document, mode=analysis_mode)
            progress.update(task, completed=True)

        # 3. 输出报告
        report.metadata.analysis_duration_ms = int((time.time() - start_time) * 1000)

        if output:
            _save_report(report, output, format)
            console.print(f"[green]✓[/green] 报告已保存: {output}")
        else:
            _print_summary(report)

        logger.info(
            "analysis_completed",
            file=str(file),
            issues_found=report.summary.total_issues,
            duration_ms=report.metadata.analysis_duration_ms,
        )

    except Exception as e:
        logger.error("analysis_failed", error=str(e), file=str(file))
        console.print(f"[red]✗[/red] 分析失败: {e}")
        raise typer.Exit(code=1)


def _save_report(report: AnalysisReport, output: Path, format: str):
    """保存报告"""
    if format == "json":
        reporter = JsonReporter()
    elif format == "markdown":
        reporter = MarkdownReporter()
    elif format == "html":
        reporter = HtmlReporter()
    else:
        raise ValueError(f"不支持的格式: {format}")

    reporter.save(report, output)


def _print_summary(report: AnalysisReport):
    """打印摘要"""
    from rich.table import Table

    table = Table(title="审查结果摘要")
    table.add_column("风险等级", style="bold")
    table.add_column("数量", justify="right")

    table.add_row("🔴 严重 (Critical)", str(report.summary.critical), style="red")
    table.add_row("🟠 高风险 (High)", str(report.summary.high), style="orange")
    table.add_row("🟡 中风险 (Medium)", str(report.summary.medium), style="yellow")
    table.add_row("🟢 低风险 (Low)", str(report.summary.low), style="green")

    console.print(table)

    if report.summary.total_issues > 0:
        console.print(f"\n发现 [bold]{report.summary.total_issues}[/bold] 个风险点")
    else:
        console.print("\n[green]✓ 未发现风险点[/green]")


# 导入 typer 以在异常时使用
import typer
