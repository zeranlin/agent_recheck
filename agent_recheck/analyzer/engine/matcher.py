"""规则匹配器"""

import re
from dataclasses import dataclass, field
from typing import Optional, List

from ...models.document import Document
from ...models.rule import Rule, RuleMatchResult
from ...utils.logging import get_logger

logger = get_logger("engine.matcher")


@dataclass
class MatchingResult:
    """匹配结果"""
    issues: List = field(default_factory=list)
    total_matches: int = 0
    high_risk_count: int = 0


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
            if rule.pattern is None:
                return RuleMatchResult(rule_id=rule.id, rule_name=rule.name, matched=False)
            
            pattern_type = rule.pattern.type

            if pattern_type == "regex":
                return self._match_regex(rule, document)
            elif pattern_type == "keyword":
                return self._match_keyword(rule, document)
            elif pattern_type == "composite":
                return self._match_composite(rule, document)
            else:
                logger.warning("unknown_pattern_type", type=pattern_type)
                return RuleMatchResult(rule_id=rule.id, rule_name=rule.name, matched=False)

        except Exception as e:
            logger.error("match_failed", rule_id=rule.id, error=str(e))
            return RuleMatchResult(rule_id=rule.id, rule_name=rule.name, matched=False)

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
            rule_id=rule.id,
            rule_name=rule.name,
            matched=matched,
            confidence=confidence,
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
            rule_id=rule.id,
            rule_name=rule.name,
            matched=matched,
            confidence=0.8 if matched else 0.0,
            location=locations[0] if locations else None,
        )

    def _match_composite(self, rule: Rule, document: Document) -> RuleMatchResult:
        """复合条件匹配"""
        if not rule.pattern:
            return RuleMatchResult(rule_id=rule.id, rule_name=rule.name, matched=False)
        
        conditions = rule.pattern.conditions
        if not conditions:
            return RuleMatchResult(rule_id=rule.id, rule_name=rule.name, matched=False)

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
            rule_id=rule.id,
            rule_name=rule.name,
            matched=matched,
            confidence=0.7 if matched else 0.0,
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

    def match_document(self, document: Document, rules: List[Rule]) -> MatchingResult:
        """
        匹配文档与所有规则

        Args:
            document: 文档
            rules: 规则列表

        Returns:
            匹配结果
        """
        from ...models.issue import Issue, IssueLevel, IssueLocation, IssueRule

        issues = []
        for rule in rules:
            if not rule.enabled:
                continue

            try:
                result = self.match(rule, document)
                if result.matched:
                    severity = IssueLevel.HIGH if rule.severity.value == "high" else \
                              IssueLevel.MEDIUM if rule.severity.value == "medium" else IssueLevel.LOW
                    
                    location = IssueLocation()
                    if result.location:
                        location.line = result.location.get("line", 0)
                        location.start = result.location.get("start", 0)
                        location.end = result.location.get("end", 0)
                    
                    issue = Issue(
                        title=rule.name,
                        description=rule.description or "",
                        level=severity,
                        category=rule.category.value if hasattr(rule.category, 'value') else str(rule.category),
                        location=location,
                        source="rule",
                        rule=IssueRule(rule_id=rule.id, rule_name=rule.name)
                    )
                    issues.append(issue)
            except Exception as e:
                logger.error("rule_match_failed", rule_id=rule.id, error=str(e))

        return MatchingResult(
            issues=issues,
            total_matches=len(issues),
            high_risk_count=sum(1 for i in issues if i.level == IssueLevel.HIGH)
        )
