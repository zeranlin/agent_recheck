"""knowledge 命令实现"""

from rich.console import Console
from rich.table import Table

from agent_recheck.knowledge.sync import KnowledgeSync
from agent_recheck.utils.path import PathUtils
from agent_recheck.utils.logging import get_logger

logger = get_logger("cli.knowledge")
console = Console()


def knowledge_command(action: str):
    """知识库管理命令"""
    if action == "status":
        _show_status()
    elif action == "sync":
        _sync_knowledge()
    elif action == "export":
        _export_knowledge()
    else:
        console.print(f"[red]错误: 未知操作 '{action}'[/red]")
        raise typer.Exit(code=1)


def _show_status():
    """显示知识库状态"""
    sync = KnowledgeSync()

    # 法规状态
    regulations = sync.get_regulations_status()

    table = Table(title="知识库状态")
    table.add_column("法规", style="cyan")
    table.add_column("版本", justify="center")
    table.add_column("状态", justify="center")

    for reg in regulations:
        status_style = {
            "effective": "green",
            "superseded": "yellow",
            "draft": "red",
        }.get(reg.get("status", ""), "")

        table.add_row(
            reg["name"],
            reg.get("version", "-"),
            f"[{status_style}]{reg.get('status', 'unknown')}[/{status_style}]",
        )

    console.print(table)


def _sync_knowledge():
    """同步知识库"""
    console.print("[bold]正在同步知识库...[/bold]")

    sync = KnowledgeSync()
    try:
        result = sync.sync_all()
        console.print(f"[green]✓[/green] 同步完成")
        console.print(f"  更新的法规: {result.get('updated', 0)}")
        console.print(f"  新增的法规: {result.get('added', 0)}")
    except Exception as e:
        logger.error("sync_failed", error=str(e))
        console.print(f"[red]✗[/red] 同步失败: {e}")


def _export_knowledge():
    """导出知识库"""
    output = PathUtils.get_knowledge_dir() / "export"
    console.print(f"[bold]正在导出知识库...[/bold] (目标: {output})")

    sync = KnowledgeSync()
    try:
        sync.export(output)
        console.print(f"[green]✓[/green] 导出完成: {output}")
    except Exception as e:
        logger.error("export_failed", error=str(e))
        console.print(f"[red]✗[/red] 导出失败: {e}")


import typer
