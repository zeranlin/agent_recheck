"""evaluate 命令实现"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from agent_recheck.evaluator.accuracy_evaluator import AccuracyEvaluator
from agent_recheck.utils.logging import get_logger

logger = get_logger("cli.evaluate")
console = Console()


def evaluate_command(
    test_set: Optional[Path],
    report: bool = False,
    output: Optional[Path] = None,
):
    """评估准确性"""
    if not test_set:
        test_set = Path("tests/fixtures/annotated")

    console.print(f"[bold]开始评估...[/bold]")
    console.print(f"测试集: {test_set}")

    evaluator = AccuracyEvaluator()

    try:
        metrics = evaluator.evaluate(test_set)

        # 打印结果
        console.print("\n[bold]评估结果:[/bold]")
        console.print(f"  Precision（准确率）: {metrics['precision']:.1%}")
        console.print(f"  Recall（召回率）: {metrics['recall']:.1%}")
        console.print(f"  F1 Score: {metrics['f1_score']:.1%}")
        console.print(f"  误报率: {metrics['false_positive_rate']:.1%}")

        # 检查是否达标
        precision_ok = metrics['precision'] >= 0.85
        recall_ok = metrics['recall'] >= 0.90

        console.print("\n[bold]达标情况:[/bold]")
        console.print(f"  Precision ≥ 85%: {'✓' if precision_ok else '✗'}")
        console.print(f"  Recall ≥ 90%: {'✓' if recall_ok else '✗'}")

        if report and output:
            evaluator.generate_report(metrics, output)
            console.print(f"\n[green]✓[/green] 报告已保存: {output}")

    except Exception as e:
        logger.error("evaluation_failed", error=str(e))
        console.print(f"[red]✗[/red] 评估失败: {e}")
        raise typer.Exit(code=1)
