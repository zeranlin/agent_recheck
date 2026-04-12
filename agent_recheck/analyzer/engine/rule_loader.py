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
        """解析规则数据 - 支持多种格式"""
        # 复制数据避免修改原数据
        data = dict(data)

        # 统一 severity/level/risk_level 字段
        if "level" in data and "severity" not in data:
            data["severity"] = data.pop("level")
        elif "risk_level" in data and "severity" not in data:
            data["severity"] = data.pop("risk_level")
        elif "level" in data and "severity" in data:
            data.pop("level")

        # 统一 category 字段 (中文/英文映射)
        if "category" in data:
            cat_map = {
                "歧视性": "discrimination",
                "非歧视性": "discrimination",
                "采购需求": "procurement",
                "评分标准": "scoring",
                "合同条款": "contract",
                "认证证书": "certification",
            }
            if data["category"] in cat_map:
                data["category"] = cat_map[data["category"]]

        # 处理 patterns 数组格式 (新格式)
        if "patterns" in data and isinstance(data["patterns"], list):
            patterns_list = []
            for p in data["patterns"]:
                if isinstance(p, dict) and "pattern" in p:
                    patterns_list.append(p["pattern"])
                elif isinstance(p, str):
                    patterns_list.append(p)
            data["patterns"] = patterns_list

        # 处理 legal_basis 数组格式 -> reference
        if "legal_basis" in data and isinstance(data["legal_basis"], list):
            if "reference" not in data:
                lb = data["legal_basis"][0] if data["legal_basis"] else {}
                data["reference"] = {
                    "law": lb.get("name", ""),
                    "article": lb.get("article", ""),
                    "full_text": lb.get("content", "")
                }
            data.pop("legal_basis")

        # 解析嵌套对象
        if "pattern" in data:
            if isinstance(data["pattern"], dict):
                # 处理 match 字段
                pattern_data = data["pattern"]
                if "match" in pattern_data and isinstance(pattern_data["match"], list):
                    pattern_data["match"] = [str(m) for m in pattern_data["match"]]
                # 处理 exclude_context 字段
                if "exclude_context" in pattern_data and isinstance(pattern_data["exclude_context"], list):
                    pattern_data["exclude_context"] = [str(c) for c in pattern_data["exclude_context"]]
                try:
                    data["pattern"] = PatternMatch(**pattern_data)
                except Exception:
                    data["pattern"] = None

        if "reference" in data and isinstance(data["reference"], dict):
            try:
                data["reference"] = RuleReference(**data["reference"])
            except Exception:
                data["reference"] = None

        if "suggestion" in data and isinstance(data["suggestion"], dict):
            suggestion_data = dict(data["suggestion"])
            # 处理 examples -> example
            if "examples" in suggestion_data:
                examples = suggestion_data.pop("examples")
                if isinstance(examples, list) and examples:
                    suggestion_data["example"] = examples[0]
            # 处理 default_suggestion -> template
            if "default_suggestion" in suggestion_data:
                suggestion_data["template"] = suggestion_data.pop("default_suggestion")
            try:
                data["suggestion"] = RuleSuggestion(**suggestion_data)
            except Exception:
                data["suggestion"] = None

        # 处理枚举值
        if isinstance(data.get("category"), str):
            for cat in RuleCategory:
                if cat.value == data["category"] or cat.name == data["category"]:
                    data["category"] = cat
                    break

        if isinstance(data.get("severity"), str):
            for lvl in RiskLevel:
                if lvl.value == data["severity"] or lvl.name == data["severity"]:
                    data["severity"] = lvl
                    break

        # 处理 legal_basis 字符串
        if "legal_basis" in data and isinstance(data["legal_basis"], str):
            data["legal_basis"] = data["legal_basis"]

        # 过滤不支持的字段
        supported_fields = [
            "id", "name", "category", "severity", "description",
            "pattern", "patterns", "keywords", "reference", "references",
            "suggestion", "suggestions", "legal_basis", "verification",
            "enabled", "confidence_threshold", "tags", "metadata"
        ]
        filtered_data = {k: v for k, v in data.items() if k in supported_fields or v is None}

        return Rule(**filtered_data)

    def export_rules(self, rules: list[Rule], output: Path):
        """导出规则到 JSON"""
        data = [rule.model_dump() for rule in rules]

        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("rules_exported", count=len(rules), output=str(output))
