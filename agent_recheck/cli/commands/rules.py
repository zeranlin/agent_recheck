"""rules 命令实现"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from analyzer.engine.rule_loader import RuleLoader
from utils.logging import get_logger

logger = get_logger("cli.rules")
console = Console()


def rules_command(action: str, file: Optional[Path]):
    """规则管理命令"""
    if action == "list":
        _list_rules()
    elif action == "add":
        if not file:
            console.print("[red]错误: 请指定规则文件路径[/red]")
            raise typer.Exit(code=1)
        _add_rule(file)
    elif action == "validate":
        if file:
            _validate_rule(file)
        else:
            _validate_all_rules()
    elif action == "export":
        _export_rules()
    else:
        console.print(f"[red]错误: 未知操作 '{action}'[/red]")
        raise typer.Exit(code=1)


def _list_rules():
    """列出所有规则"""
    loader = RuleLoader()
    rules = loader.load_all()

    table = Table(title="规则列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="bold")
    table.add_column("类别", style="magenta")
    table.add_column("风险等级", justify="center")

    for rule in rules:
        level_style = {
            "critical": "red",
            "high": "orange",
            "medium": "yellow",
            "low": "green",
        }.get(rule.level, "")

        table.add_row(
            rule.id,
            rule.name,
            rule.category,
            f"[{level_style}]{rule.level.upper()}[/{level_style}]",
        )

    console.print(table)
    console.print(f"\n共 {len(rules)} 条规则")


def _add_rule(file: Path):
    """添加规则"""
    loader = RuleLoader()
    try:
        rule = loader.load_from_file(file)
        console.print(f"[green]✓[/green] 规则已添加: {rule.id} - {rule.name}")
    except Exception as e:
        console.print(f"[red]✗[/red] 添加规则失败: {e}")
        raise typer.Exit(code=1)


def _validate_rule(file: Path):
    """验证单个规则文件"""
    loader = RuleLoader()
    try:
        rule = loader.load_from_file(file)
        console.print(f"[green]✓[/green] 规则验证通过: {rule.id}")
    except Exception as e:
        console.print(f"[red]✗[/red] 规则验证失败: {e}")
        raise typer.Exit(code=1)


def _validate_all_rules():
    """验证所有规则"""
    loader = RuleLoader()
    rules = loader.load_all()

    errors = []
    for rule in rules:
        if not rule.validate():
            errors.append(rule.id)

    if errors:
        console.print(f"[red]✗[/red] {len(errors)} 条规则验证失败:")
        for rule_id in errors:
            console.print(f"  - {rule_id}")
        raise typer.Exit(code=1)
    else:
        console.print(f"[green]✓[/green] 所有 {len(rules)} 条规则验证通过")


def _export_rules():
    """导出规则"""
    loader = RuleLoader()
    rules = loader.load_all()

    output = Path("rules_export.json")
    loader.export_rules(rules, output)

    console.print(f"[green]✓[/green] 规则已导出: {output}")
