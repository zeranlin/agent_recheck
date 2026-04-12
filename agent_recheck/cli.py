# -*- coding: utf-8 -*-
"""
CLI 命令行工具

提供命令行界面进行招标文件合规性审查
"""

import argparse
import sys
import os
from typing import Optional
import logging

from .analyzer.workflow import ReviewWorkflow, ReviewConfig, BatchReviewWorkflow
from .analyzer.parser.docx_parser import DocxParser
from .analyzer.parser.pdf_parser import PdfParser
from .analyzer.engine.rule_loader import RuleLoader
from .analyzer.engine.hybrid_engine import HybridEngine
from .report.report_builder import ReportBuilder, ReportConfig as ReportConf


def setup_logging(verbose: bool = False) -> None:
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def cmd_parse(args) -> int:
    """解析文档命令"""
    setup_logging(args.verbose)

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在: {args.input}")
        return 1

    print(f"正在解析文档: {args.input}")

    ext = os.path.splitext(args.input)[1].lower()
    if ext == ".docx":
        parser = DocxParser()
    elif ext == ".pdf":
        parser = PdfParser()
    else:
        print(f"错误: 不支持的格式: {ext}")
        return 1

    document = parser.parse(args.input)

    print(f"\n解析完成!")
    print(f"  页数/章节: {document.metadata.get('page_count', 'N/A')}")
    print(f"  段落数: {len(document.paragraphs)}")
    print(f"  表格数: {len(document.tables)}")
    print(f"  标题数: {len(document.sections)}")

    if args.output:
        import json
        output_data = {
            "metadata": document.metadata,
            "paragraphs": [p.text for p in document.paragraphs[:10]],
            "sections": [{"title": s.title, "level": s.level} for s in document.sections[:20]],
            "tables": [{"rows": len(t.rows) if hasattr(t, 'rows') else 0, "cols": len(t.rows[0]) if hasattr(t, 'rows') and t.rows else 0} for t in document.tables[:10]]
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")

    return 0


def cmd_rules(args) -> int:
    """列出规则命令"""
    setup_logging(args.verbose)

    loader = RuleLoader()
    rules = loader.load_all_rules()

    print(f"\n已加载 {len(rules)} 条规则:\n")

    by_category = {}
    for rule in rules:
        category = rule.get("category", "other")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(rule)

    for category, category_rules in sorted(by_category.items()):
        print(f"  [{category}] ({len(category_rules)} 条)")
        for rule in category_rules[:5]:
            rule_id = rule.get("id", "unknown")
            name = rule.get("name", "未命名")
            print(f"    - {rule_id}: {name}")
        if len(category_rules) > 5:
            print(f"    ... 还有 {len(category_rules) - 5} 条")
        print()

    return 0


def cmd_check(args) -> int:
    """审查文档命令"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在: {args.input}")
        return 1

    print(f"正在审查文档: {args.input}")
    print("-" * 50)

    config = ReviewConfig(
        enable_llm=not args.no_llm,
        enable_consistency=not args.no_consistency,
        enable_local_rules=not args.no_local,
        max_llm_calls=args.max_llm_calls,
        confidence_threshold=args.threshold,
        output_formats=[args.format] if args.format else ["json", "markdown"],
        output_path=args.output_dir
    )

    workflow = ReviewWorkflow(config)
    task = workflow.create_task(args.input)

    try:
        result = workflow.execute_task(task)

        print(f"\n审查完成!")
        print(f"  任务ID: {result['task_id']}")
        print(f"  发现问题: {len(result['result'].issues)} 个")

        by_severity = {"high": 0, "medium": 0, "low": 0}
        for issue in result['result'].issues:
            sev = issue.severity.value if hasattr(issue, 'severity') else "low"
            if sev in by_severity:
                by_severity[sev] += 1

        print(f"    - 高风险: {by_severity['high']} 个")
        print(f"    - 中风险: {by_severity['medium']} 个")
        print(f"    - 低风险: {by_severity['low']} 个")

        if result.get("consistency"):
            cons = result["consistency"]
            print(f"\n一致性检查:")
            print(f"  发现问题: {len(cons.issues)} 个")
            print(f"  状态: {'通过' if cons.is_consistent else '存在问题'}")

        if args.format == "markdown" and "markdown" in result.get("reports", {}):
            print("\n" + "=" * 50)
            print(result["reports"]["markdown"])
        elif args.format == "html" and "html" in result.get("reports", {}):
            html_file = f"{args.output_dir or '.'}/{task.task_id}.html"
            print(f"\nHTML报告已保存到: {html_file}")

        return 0

    except Exception as e:
        logger.error(f"审查失败: {e}", exc_info=args.verbose)
        print(f"\n错误: {e}")
        return 1


def cmd_batch(args) -> int:
    """批量审查命令"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    files = []
    if os.path.isdir(args.input):
        for ext in ["*.docx", "*.pdf"]:
            files.extend([
                os.path.join(args.input, f)
                for f in os.listdir(args.input)
                if f.endswith(ext)
            ])
    elif os.path.isfile(args.input):
        with open(args.input, "r") as f:
            files = [line.strip() for line in f if line.strip()]

    if not files:
        print("错误: 未找到要审查的文件")
        return 1

    print(f"找到 {len(files)} 个文件待审查")
    print("-" * 50)

    config = ReviewConfig(
        enable_llm=not args.no_llm,
        enable_consistency=not args.no_consistency,
        output_formats=["json"],
        output_path=args.output_dir
    )

    workflow = BatchReviewWorkflow(config)

    for f in files:
        print(f"添加任务: {f}")
        workflow.add_task(f)

    results = workflow.execute_all(max_parallel=args.parallel)

    print("\n" + "=" * 50)
    summary = workflow.get_summary()
    print(f"批量审查完成!")
    print(f"  总任务: {summary['total_tasks']}")
    print(f"  已完成: {summary['completed']}")
    print(f"  失败: {summary['failed']}")
    print(f"  发现问题总数: {summary['total_issues']}")

    return 0


def cmd_validate(args) -> int:
    """验证规则命令"""
    setup_logging(args.verbose)

    loader = RuleLoader()
    rules = loader.load_all_rules()

    valid_count = 0
    invalid_count = 0

    print(f"正在验证 {len(rules)} 条规则...\n")

    for rule in rules:
        is_valid, errors = _validate_rule(rule)

        if is_valid:
            valid_count += 1
            print(f"✓ {rule.get('id', 'unknown')}: 有效")
        else:
            invalid_count += 1
            print(f"✗ {rule.get('id', 'unknown')}: 无效")
            for error in errors:
                print(f"    - {error}")

    print(f"\n验证完成: {valid_count} 有效, {invalid_count} 无效")
    return 0 if invalid_count == 0 else 1


def _validate_rule(rule: dict) -> tuple[bool, list[str]]:
    """验证单条规则"""
    errors = []

    required_fields = ["id", "name", "category", "severity", "patterns"]
    for field in required_fields:
        if field not in rule:
            errors.append(f"缺少必需字段: {field}")

    if "patterns" in rule:
        if not isinstance(rule["patterns"], list):
            errors.append("patterns 必须是列表")
        elif len(rule["patterns"]) == 0:
            errors.append("patterns 不能为空")

    if "severity" in rule:
        valid_severities = ["high", "medium", "low"]
        if rule["severity"] not in valid_severities:
            errors.append(f"severity 必须是 {valid_severities} 之一")

    return len(errors) == 0, errors


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="招标文件合规性审查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s parse document.docx -o result.json
  %(prog)s rules
  %(prog)s check document.pdf --format markdown
  %(prog)s batch ./documents/
  %(prog)s validate
        """
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 子命令
    parse_parser = subparsers.add_parser("parse", help="解析文档")
    parse_parser.add_argument("input", help="输入文件路径")
    parse_parser.add_argument("-o", "--output", help="输出JSON文件路径")
    parse_parser.set_defaults(func=cmd_parse)

    # rules 子命令
    rules_parser = subparsers.add_parser("rules", help="列出所有规则")
    rules_parser.set_defaults(func=cmd_rules)

    # check 子命令
    check_parser = subparsers.add_parser("check", help="审查文档")
    check_parser.add_argument("input", help="输入文件路径")
    check_parser.add_argument("-f", "--format", choices=["json", "markdown", "html"], help="输出格式")
    check_parser.add_argument("-o", "--output-dir", help="输出目录")
    check_parser.add_argument("--no-llm", action="store_true", help="禁用LLM分析")
    check_parser.add_argument("--no-consistency", action="store_true", help="禁用一致性检查")
    check_parser.add_argument("--no-local", action="store_true", help="禁用本地化规则")
    check_parser.add_argument("--max-llm-calls", type=int, default=50, help="最大LLM调用次数")
    check_parser.add_argument("--threshold", type=float, default=0.7, help="置信度阈值")
    check_parser.set_defaults(func=cmd_check)

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量审查")
    batch_parser.add_argument("input", help="输入目录或文件列表")
    batch_parser.add_argument("-o", "--output-dir", help="输出目录")
    batch_parser.add_argument("--parallel", type=int, default=3, help="并行任务数")
    batch_parser.add_argument("--no-llm", action="store_true", help="禁用LLM分析")
    batch_parser.add_argument("--no-consistency", action="store_true", help="禁用一致性检查")
    batch_parser.set_defaults(func=cmd_batch)

    # validate 子命令
    validate_parser = subparsers.add_parser("validate", help="验证规则")
    validate_parser.set_defaults(func=cmd_validate)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
