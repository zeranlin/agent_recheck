"""stats 命令实现"""

from rich.console import Console
from rich.table import Table

from agent_recheck.tracker.metrics import MetricsTracker
from agent_recheck.utils.logging import get_logger

logger = get_logger("cli.stats")
console = Console()


def stats_command(metric: str = None):
    """显示监控统计"""
    tracker = MetricsTracker()

    if metric:
        _show_single_metric(tracker, metric)
    else:
        _show_all_metrics(tracker)


def _show_single_metric(tracker: MetricsTracker, metric_name: str):
    """显示单个指标"""
    value = tracker.get_metric(metric_name)
    console.print(f"[bold]{metric_name}:[/bold] {value}")


def _show_all_metrics(tracker: MetricsTracker):
    """显示所有指标"""
    metrics = tracker.get_all_metrics()

    table = Table(title="监控指标")
    table.add_column("指标", style="cyan")
    table.add_column("值", justify="right")

    for name, value in metrics.items():
        table.add_row(name, str(value))

    console.print(table)
