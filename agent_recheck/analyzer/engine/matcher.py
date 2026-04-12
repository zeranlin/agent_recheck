"""规则匹配器"""

import re
from typing import Optional

from models.document import Document
from models.rule import Rule, RuleMatchResult
from utils.logging import get_logger

logger = get_logger("engine.matcher")


class RuleMatcher:
    """规则匹配器"""

    def __init__(self):
        self.compiled_patterns: dict[str, re.Pattern] = {}

    def match(self, rule: Rule, document: Document) -> RuleMatchResult:
        """
        匹配规则

        Args:
            rule: 规则
            document: 文档

        Returns:
            匹配结果
        """
        try:
            # 根据匹配类型执行匹配
            pattern_type = rule.pattern.type

            if pattern_type == "regex":
                return self._match_regex(rule, document)
            elif pattern_type == "keyword":
                return self._match_keyword(rule, document)
            elif pattern_type == "composite":
                return self._match_composite(rule, document)
            else:
                logger.warning("unknown_pattern_type", type=pattern_type)
                return RuleMatchResult(rule=rule, matched=False)

        except Exception as e:
            logger.error("match_failed", rule_id=rule.id, error=str(e))
            return RuleMatchResult(rule=rule, matched=False)

    def _match_regex(self, rule: Rule, document: Document) -> RuleMatchResult:
        """正则匹配"""
        matched_texts = []
        locations = []

        for pattern_str in rule.pattern.match:
            pattern = self._get_compiled_pattern(pattern_str)

            for match in pattern.finditer(document.full_text):
                matched_text = match.group()
                line_num = document.full_text[:match.start()].count("\n") + 1

                # 检查排除上下文
                if not self._is_excluded(match.group(), rule.pattern.exclude_context):
                    matched_texts.append(matched_text)
                    locations.append({
                        "line": line_num,
                        "start": match.start(),
                        "end": match.end(),
                    })

        matched = len(matched_texts) > 0
        confidence = 1.0 if matched else 0.0

        return RuleMatchResult(
            rule=rule,
            matched=matched,
            confidence=confidence,
            matched_text=matched_texts[0] if matched_texts else None,
            location=locations[0] if locations else None,
        )

    def _match_keyword(self, rule: Rule, document: Document) -> RuleMatchResult:
        """关键词匹配"""
        matched_texts = []
        locations = []

        for keyword in rule.pattern.match:
            pattern = rf".{{0,50}}{re.escape(keyword)}.{{0,50}}"

            for match in re.finditer(pattern, document.full_text):
                matched_text = match.group()
                line_num = document.full_text[:match.start()].count("\n") + 1

                if not self._is_excluded(matched_text, rule.pattern.exclude_context):
                    matched_texts.append(matched_text)
                    locations.append({
                        "line": line_num,
                        "start": match.start(),
                        "end": match.end(),
                    })

        matched = len(matched_texts) > 0

        return RuleMatchResult(
            rule=rule,
            matched=matched,
            confidence=0.8 if matched else 0.0,
            matched_text=matched_texts[0] if matched_texts else None,
            location=locations[0] if locations else None,
        )

    def _match_composite(self, rule: Rule, document: Document) -> RuleMatchResult:
        """复合条件匹配"""
        conditions = rule.pattern.conditions
        if not conditions:
            return RuleMatchResult(rule=rule, matched=False)

        # 所有条件都满足才算匹配
        matched = True
        matched_text = None

        for condition in conditions:
            keyword = condition.get("keyword")
            level_match = condition.get("level_match")

            if keyword and keyword not in document.full_text:
                matched = False
                break

            if level_match:
                pattern = re.compile(level_match)
                if not pattern.search(document.full_text):
                    matched = False
                    break

        if matched:
            # 找到匹配的文本
            for keyword in rule.pattern.match:
                if keyword in document.full_text:
                    matched_text = keyword
                    break

        return RuleMatchResult(
            rule=rule,
            matched=matched,
            confidence=0.7 if matched else 0.0,
            matched_text=matched_text,
        )

    def _get_compiled_pattern(self, pattern_str: str) -> re.Pattern:
        """获取编译后的正则"""
        if pattern_str not in self.compiled_patterns:
            self.compiled_patterns[pattern_str] = re.compile(pattern_str)
        return self.compiled_patterns[pattern_str]

    def _is_excluded(self, text: str, exclude_contexts: list[str]) -> bool:
        """检查是否在排除上下文中"""
        for ctx in exclude_contexts:
            if ctx in text:
                return True
        return False
