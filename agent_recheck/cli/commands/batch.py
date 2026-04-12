"""batch 命令实现"""

import asyncio
import json
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from analyzer.engine.hybrid_engine import HybridAnalysisEngine
from analyzer.parser.base import ParserFactory
from ...models.report import AnalysisReport
from report.json_reporter import JsonReporter
from ..utils.logging import get_logger

logger = get_logger("cli.batch")
console = Console()


def batch_command(
    directory: Path,
    output: Optional[Path],
    format: str = "json",
    parallel: int = 4,
    no_llm: bool = False,
):
    """批量分析目录中的文件"""
    # 收集文件
    files = _collect_files(directory)

    if not files:
        console.print("[yellow]未找到支持的文件[/yellow]")
        return

    console.print(f"[bold]找到 {len(files)} 个文件[/bold]")

    # 创建输出目录
    if output:
        output_dir = output
    else:
        output_dir = directory / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 分析模式
    analysis_mode = "rules_only" if no_llm else "hybrid"

    # 并行分析
    results = []
    engine = HybridAnalysisEngine()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("分析中...", total=len(files))

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(_analyze_file, file, engine, analysis_mode, output_dir, format): file
                for file in files
            }

            for future in futures:
                result = future.result()
                results.append(result)
                progress.advance(task)

    # 输出汇总
    _print_batch_summary(results, output_dir)


def _collect_files(directory: Path) -> list[Path]:
    """收集支持的文件"""
    files = []
    for ext in [".docx", ".doc", ".pdf"]:
        files.extend(directory.rglob(f"*{ext}"))
    return files


def _analyze_file(
    file: Path,
    engine: HybridAnalysisEngine,
    mode: str,
    output_dir: Path,
    format: str,
) -> dict:
    """分析单个文件"""
    try:
        parser = ParserFactory.create_parser(file)
        document = parser.parse(file)
        report = engine.analyze(document, mode=mode)

        # 保存报告
        output_file = output_dir / f"{file.stem}_report.{format}"
        reporter = JsonReporter()
        reporter.save(report, output_file)

        return {
            "file": file.name,
            "success": True,
            "issues": report.summary.total_issues,
            "output": str(output_file),
        }
    except Exception as e:
        logger.error("batch_file_failed", file=str(file), error=str(e))
        return {
            "file": file.name,
            "success": False,
            "error": str(e),
        }


def _print_batch_summary(results: list[dict], output_dir: Path):
    """打印批量分析汇总"""
    table = Table(title="批量分析结果")
    table.add_column("状态", justify="center")
    table.add_column("文件", style="cyan")
    table.add_column("风险点", justify="right")

    success_count = 0
    total_issues = 0

    for result in results:
        status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
        issues = str(result.get("issues", "-"))

        if result["success"]:
            success_count += 1
            total_issues += result.get("issues", 0)

        table.add_row(status, result["file"], issues)

    console.print(table)
    console.print(f"\n成功: {success_count}/{len(results)}")
    console.print(f"总风险点: {total_issues}")
    console.print(f"报告目录: {output_dir}")
