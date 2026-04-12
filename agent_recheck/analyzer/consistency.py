# -*- coding: utf-8 -*-
"""
一致性检查模块

对解析后的内容进行一致性检查，包括：
1. 资质要求前后一致
2. 评分标准与分值匹配
3. 表格数据与文字描述一致
4. 时间节点逻辑正确
"""

from typing import Any
from dataclasses import dataclass, field
from enum import Enum
from ..parser.base import ParsedDocument
from ..parser.enhanced_table_parser import EnhancedTableParser, TableType
from ..engine.scoring_parser import ScoringParser


class ConsistencyType(Enum):
    """一致性检查类型"""
    QUALIFICATION = "qualification"          # 资质要求一致
    SCORING = "scoring"                       # 评分标准一致
    TABLE_TEXT = "table_text"                # 表格与文字一致
    TIMELINE = "timeline"                    # 时间节点逻辑
    AMOUNT = "amount"                         # 金额数字一致
    NAME = "name"                             # 名称一致


class Severity(Enum):
    """严重程度"""
    ERROR = "error"           # 错误，必须修复
    WARNING = "warning"       # 警告，建议检查
    INFO = "info"             # 信息，供参考


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    check_type: ConsistencyType
    severity: Severity
    title: str
    description: str
    location: dict = field(default_factory=dict)  # {section, page, line}
    evidence: list[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass
class ConsistencyResult:
    """一致性检查结果"""
    is_consistent: bool
    issues: list[ConsistencyIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)  # {severity: count}
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ConsistencyIssue) -> None:
        self.issues.append(issue)
        severity_key = issue.severity.value
        self.summary[severity_key] = self.summary.get(severity_key, 0) + 1
        if issue.severity == Severity.ERROR:
            self.is_consistent = False

    def get_issues_by_type(self, check_type: ConsistencyType) -> list[ConsistencyIssue]:
        return [i for i in self.issues if i.check_type == check_type]

    def get_issues_by_severity(self, severity: Severity) -> list[ConsistencyIssue]:
        return [i for i in self.issues if i.severity == severity]


class ConsistencyChecker:
    """一致性检查器"""

    def __init__(self, document: ParsedDocument):
        self.document = document
        self.table_parser = EnhancedTableParser()
        self.scoring_parser = ScoringParser()
        self.result = ConsistencyResult(is_consistent=True)

    def check_all(self) -> ConsistencyResult:
        """执行所有一致性检查"""
        self._check_qualification_consistency()
        self._check_scoring_consistency()
        self._check_table_text_consistency()
        self._check_timeline_consistency()
        self._check_amount_consistency()
        self._check_name_consistency()
        return self.result

    def _check_qualification_consistency(self) -> None:
        """检查资质要求前后一致"""
        qualifications = []
        for section in self.document.sections:
            for para in section.paragraphs:
                text = para.text
                if any(kw in text for kw in ["资质", "要求", "具备", "持有"]):
                    qualifications.append({
                        "text": text,
                        "section": section.title,
                        "location": para.metadata
                    })

        seen_qualifications = {}
        for qual in qualifications:
            for key_phrase in self._extract_key_phrases(qual["text"]):
                if key_phrase in seen_qualifications:
                    prev = seen_qualifications[key_phrase]
                    if not self._compare_qualification(qual, prev):
                        self.result.add_issue(ConsistencyIssue(
                            check_type=ConsistencyType.QUALIFICATION,
                            severity=Severity.WARNING,
                            title="资质要求不一致",
                            description=f"'{key_phrase}' 在不同位置的描述存在差异",
                            location=qual["location"],
                            evidence=[qual["text"], prev["text"]],
                            suggestion="确认资质要求是否为同一标准"
                        ))
                else:
                    seen_qualifications[key_phrase] = qual

    def _check_scoring_consistency(self) -> None:
        """检查评分标准与分值匹配"""
        scoring_tables = []
        for table in self.document.tables:
            if table.get("type") == TableType.SCORING or "评分" in table.get("title", ""):
                scoring_tables.append(table)

        for table in scoring_tables:
            total_weight = 0
            for row in table.get("rows", []):
                if row.get("is_header"):
                    continue
                weight = self._extract_number(row.get("cells", [{}])[-1].get("text", ""))
                total_weight += weight

            if total_weight > 0 and abs(total_weight - 100) > 0.5:
                self.result.add_issue(ConsistencyIssue(
                    check_type=ConsistencyType.SCORING,
                    severity=Severity.ERROR if abs(total_weight - 100) > 5 else Severity.WARNING,
                    title="评分权重不等于100%",
                    description=f"评分表中各项权重之和为 {total_weight}%，不等于100%",
                    location=table.get("metadata", {}),
                    evidence=[str(table.get("title", "")), f"总和: {total_weight}%"],
                    suggestion="调整各评分项权重使其总和为100%"
                ))

    def _check_table_text_consistency(self) -> None:
        """检查表格数据与文字描述一致"""
        table_titles = set()
        for table in self.document.tables:
            title = table.get("title", "")
            if title:
                table_titles.add(title)

        for section in self.document.sections:
            for para in section.paragraphs:
                para_text = para.text
                for title in table_titles:
                    if title in para_text and "见下表" in para_text:
                        related_tables = [t for t in self.document.tables if t.get("title") == title]
                        if not related_tables:
                            self.result.add_issue(ConsistencyIssue(
                                check_type=ConsistencyType.TABLE_TEXT,
                                severity=Severity.WARNING,
                                title="表格引用但未找到",
                                description=f"文档引用表格 '{title}'，但未找到该表格",
                                location=para.metadata,
                                evidence=[para_text],
                                suggestion="检查表格是否存在或编号是否正确"
                            ))

    def _check_timeline_consistency(self) -> None:
        """检查时间节点逻辑正确"""
        dates = []
        for section in self.document.sections:
            for para in section.paragraphs:
                found_dates = self._extract_dates(para.text)
                for date in found_dates:
                    dates.append({
                        "date": date,
                        "context": para.text[:100],
                        "section": section.title
                    })

        dates.sort(key=lambda x: x["date"])

        for i in range(len(dates) - 1):
            current = dates[i]
            next_item = dates[i + 1]
            if "截止" in current["context"] or "截止" in next_item["context"]:
                if current["date"] > next_item["date"]:
                    self.result.add_issue(ConsistencyIssue(
                        check_type=ConsistencyType.TIMELINE,
                        severity=Severity.ERROR,
                        title="时间逻辑错误",
                        description=f"存在后续日期早于截止日期的情况",
                        location={"section": current["section"]},
                        evidence=[current["context"], next_item["context"]],
                        suggestion="检查时间节点顺序是否合理"
                    ))

    def _check_amount_consistency(self) -> None:
        """检查金额数字一致"""
        amounts = {}
        for section in self.document.sections:
            for para in section.paragraphs:
                found_amounts = self._extract_amounts(para.text)
                for amount, context in found_amounts:
                    if amount in amounts:
                        if not self._compare_amount_context(amount, context, amounts[amount]["context"]):
                            self.result.add_issue(ConsistencyIssue(
                                check_type=ConsistencyType.AMOUNT,
                                severity=Severity.WARNING,
                                title="金额描述不一致",
                                description=f"金额 {amount} 在不同位置描述不一致",
                                evidence=[context, amounts[amount]["context"]],
                                suggestion="确认金额是否为同一笔款项"
                            ))
                    else:
                        amounts[amount] = {"context": context, "section": section.title}

    def _check_name_consistency(self) -> None:
        """检查名称一致"""
        names = {}
        for section in self.document.sections:
            for para in section.paragraphs:
                found_names = self._extract_project_names(para.text)
                for name in found_names:
                    if name in names:
                        if not self._fuzzy_match(name, names[name]):
                            self.result.add_issue(ConsistencyIssue(
                                check_type=ConsistencyType.NAME,
                                severity=Severity.INFO,
                                title="项目名称可能不一致",
                                description=f"项目名称可能有多种写法",
                                evidence=[name, names[name]],
                                suggestion="统一项目名称写法"
                            ))
                    else:
                        names[name] = name

    def _extract_key_phrases(self, text: str) -> list[str]:
        """提取关键短语"""
        import re
        patterns = [
            r"(ISO\d+[^\s，,。]+)",
            r"([一二三甲乙丙级]+资质)",
            r"(供应商|投标人|承包商)[^\s，,。]+",
        ]
        phrases = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phrases.extend(matches)
        return phrases

    def _compare_qualification(self, q1: dict, q2: dict) -> bool:
        """比较两个资质要求是否一致"""
        text1 = q1["text"].lower()
        text2 = q2["text"].lower()
        similarity = self._calculate_similarity(text1, text2)
        return similarity > 0.8

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算文本相似度"""
        set1 = set(s1)
        set2 = set(s2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _fuzzy_match(self, s1: str, s2: str) -> bool:
        """模糊匹配"""
        import re
        clean1 = re.sub(r"[^\w]", "", s1.lower())
        clean2 = re.sub(r"[^\w]", "", s2.lower())
        return clean1 in clean2 or clean2 in clean1

    def _extract_number(self, text: str) -> float:
        """提取数字"""
        import re
        match = re.search(r"[\d.]+", text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return 0.0
        return 0.0

    def _extract_dates(self, text: str) -> list[str]:
        """提取日期"""
        import re
        patterns = [
            r"\d{4}年\d{1,2}月\d{1,2}日",
            r"\d{4}-\d{2}-\d{2}",
            r"\d{4}/\d{2}/\d{2}",
        ]
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        return dates

    def _extract_amounts(self, text: str) -> list[tuple[str, str]]:
        """提取金额"""
        import re
        pattern = r"(?:人民币|元|RMB|USD|\$)?\s*[\d,]+(?:\.\d{1,2})?\s*(?:万元|万|元|美元|USD)?"
        matches = re.findall(pattern, text)
        return [(m, text) for m in matches]

    def _extract_project_names(self, text: str) -> list[str]:
        """提取项目名称"""
        import re
        pattern = r"《([^》]+)》|([^\s，,。]{5,20}项目)"
        matches = re.findall(pattern, text)
        return [m[0] or m[1] for m in matches if m[0] or m[1]]
