"""CLI 主入口"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from utils.logging import setup_logging

# 创建 Typer 应用
app = typer.Typer(
    name="agent_recheck",
    help="政府采购招投标文件合规性审查智能体",
    add_completion=False,
)

console = Console()


@app.callback()
def main_callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
    log_file: Optional[Path] = typer.Option(None, "--log-file", help="日志文件路径"),
):
    """全局回调"""
    level = "DEBUG" if verbose else ("ERROR" if quiet else "INFO")
    setup_logging(level=level, log_file=log_file)


@app.command()
def analyze(
    file: Path = typer.Argument(..., exists=True, help="要分析的文件路径"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    format: str = typer.Option("json", "--format", "-f", help="输出格式: json/markdown/html"),
    no_llm: bool = typer.Option(False, "--no-llm", help="仅使用规则引擎"),
    llm_only: bool = typer.Option(False, "--llm-only", help="仅使用 LLM"),
    threshold: float = typer.Option(0.7, "--threshold", help="LLM 置信度阈值"),
):
    """分析单个投标文件"""
    from cli.commands.analyze import analyze_command

    analyze_command(
        file=file,
        output=output,
        format=format,
        no_llm=no_llm,
        llm_only=llm_only,
        threshold=threshold,
    )


@app.command()
def batch(
    directory: Path = typer.Argument(..., exists=True, help="目录路径"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录"),
    format: str = typer.Option("json", "--format", "-f", help="输出格式"),
    parallel: int = typer.Option(4, "--parallel", "-p", help="并行数量"),
    no_llm: bool = typer.Option(False, "--no-llm", help="仅使用规则引擎"),
):
    """批量分析目录中的文件"""
    from cli.commands.batch import batch_command

    batch_command(
        directory=directory,
        output=output,
        format=format,
        parallel=parallel,
        no_llm=no_llm,
    )


@app.command()
def rules(
    action: str = typer.Argument("list", help="操作: list/add/validate/export"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="规则文件路径"),
):
    """规则管理"""
    from cli.commands.rules import rules_command

    rules_command(action=action, file=file)


@app.command()
def evaluate(
    test_set: Optional[Path] = typer.Option(None, "--test-set", help="测试集路径"),
    report: bool = typer.Option(False, "--report", help="生成评估报告"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出路径"),
):
    """评估审查准确性"""
    from cli.commands.evaluate import evaluate_command

    evaluate_command(test_set=test_set, report=report, output=output)


@app.command()
def knowledge(
    action: str = typer.Argument("status", help="操作: sync/status/export"),
):
    """知识库管理"""
    from cli.commands.knowledge import knowledge_command

    knowledge_command(action=action)


@app.command()
def stats(
    metric: Optional[str] = typer.Option(None, "--metrics", help="指定指标"),
):
    """查看监控统计"""
    from cli.commands.stats import stats_command

    stats_command(metric=metric)


@app.command()
def version():
    """显示版本信息"""
    from __init__ import __version__

    console.print(f"[bold]agent_recheck[/bold] v{__version__}")


if __name__ == "__main__":
    app()
