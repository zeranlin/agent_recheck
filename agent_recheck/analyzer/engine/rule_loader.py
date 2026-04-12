"""规则加载器"""

import json
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from ...models.rule import Rule, RuleCategory, RiskLevel, PatternMatch, RuleReference, RuleSuggestion
from ...utils.logging import get_logger
from ...utils.path import PathUtils

logger = get_logger("engine.rule_loader")


class RuleLoader:
    """规则加载器"""

    def __init__(self, rules_dir: Optional[Path] = None):
        self.rules_dir = rules_dir or PathUtils.get_rules_dir()

    def load_all(self) -> list[Rule]:
        """加载所有规则"""
        rules = []

        # 遍历所有子目录
        for category_dir in self.rules_dir.iterdir():
            if category_dir.is_dir():
                for rule_file in category_dir.glob("*.yaml"):
                    try:
                        rule = self.load_from_file(rule_file)
                        rules.append(rule)
                    except Exception as e:
                        logger.warning("rule_load_failed", file=str(rule_file), error=str(e))

        logger.info("rules_loaded", count=len(rules))
        return rules

    def load_from_file(self, file_path: Path) -> Rule:
        """从文件加载单个规则"""
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return self._parse_rule(data)

    def load_by_category(self, category: str) -> list[Rule]:
        """按类别加载规则"""
        category_dir = self.rules_dir / category
        if not category_dir.exists():
            return []

        rules = []
        for rule_file in category_dir.glob("*.yaml"):
            try:
                rule = self.load_from_file(rule_file)
                rules.append(rule)
            except Exception as e:
                logger.warning("rule_load_failed", file=str(rule_file), error=str(e))

        return rules

    def _parse_rule(self, data: dict) -> Rule:
        """解析规则数据"""
        # 处理枚举值
        if isinstance(data.get("category"), str):
            # 转换为枚举
            for cat in RuleCategory:
                if cat.value == data["category"] or cat.name == data["category"]:
                    data["category"] = cat
                    break

        if isinstance(data.get("level"), str):
            for lvl in RiskLevel:
                if lvl.value == data["level"] or lvl.name == data["level"]:
                    data["level"] = lvl
                    break

        # 解析嵌套对象
        data["pattern"] = PatternMatch(**data.get("pattern", {}))
        data["reference"] = RuleReference(**data.get("reference", {}))
        data["suggestion"] = RuleSuggestion(**data.get("suggestion", {}))

        return Rule(**data)

    def export_rules(self, rules: list[Rule], output: Path):
        """导出规则到 JSON"""
        data = [rule.model_dump() for rule in rules]

        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("rules_exported", count=len(rules), output=str(output))
