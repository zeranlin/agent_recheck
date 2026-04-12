# -*- coding: utf-8 -*-
"""
深圳政府采购知识库

包含：
- 法规文件
- 政策解读
- 典型案例
- 常见问题
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os


@dataclass
class Regulation:
    """法规条目"""
    id: str
    title: str
    code: str  # 法规编号
    category: str  # 采购法/招标投标法/中小企业促进法等
    effective_date: str
    issuer: str
    content: str
    keywords: list[str] = field(default_factory=list)
    related_regulations: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class PolicyInterpretation:
    """政策解读"""
    id: str
    title: str
    regulation_id: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TypicalCase:
    """典型案例"""
    case_id: str
    title: str
    case_type: str  # 合规/违规
    region: str
    description: str
    violation: str
    penalty: str
    lessons: list[str] = field(default_factory=list)


@dataclass
class FAQ:
    """常见问题"""
    question: str
    answer: str
    category: str
    related_regulations: list[str] = field(default_factory=list)


class ShenzhenKnowledgeBase:
    """深圳政府采购知识库"""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or "./agent_recheck/knowledge/regulations/shenzhen"
        self.regulations: dict[str, Regulation] = {}
        self.interpretations: dict[str, PolicyInterpretation] = {}
        self.cases: dict[str, TypicalCase] = {}
        self.faqs: list[FAQ] = []

        self._load_knowledge()

    def _load_knowledge(self) -> None:
        """加载知识库"""
        self._load_regulations()
        self._load_cases()
        self._load_faqs()

    def _load_regulations(self) -> None:
        """加载法规"""
        reg_file = os.path.join(self.base_dir, "regulations.json")
        if os.path.exists(reg_file):
            with open(reg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("regulations", []):
                    reg = Regulation(**item)
                    self.regulations[reg.id] = reg

    def _load_cases(self) -> None:
        """加载案例"""
        cases_file = os.path.join(self.base_dir, "cases.json")
        if os.path.exists(cases_file):
            with open(cases_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("cases", []):
                    case = TypicalCase(**item)
                    self.cases[case.case_id] = case

    def _load_faqs(self) -> None:
        """加载FAQ"""
        faq_file = os.path.join(self.base_dir, "faqs.json")
        if os.path.exists(faq_file):
            with open(faq_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("faqs", []):
                    faq = FAQ(**item)
                    self.faqs.append(faq)

    def search_regulations(self, keyword: str) -> list[Regulation]:
        """搜索法规"""
        keyword_lower = keyword.lower()
        results = []

        for reg in self.regulations.values():
            if keyword_lower in reg.title.lower():
                results.append(reg)
            elif keyword_lower in reg.content.lower():
                results.append(reg)
            elif any(keyword_lower in k.lower() for k in reg.keywords):
                results.append(reg)

        return results

    def get_regulation_by_code(self, code: str) -> Optional[Regulation]:
        """根据编号获取法规"""
        for reg in self.regulations.values():
            if reg.code == code:
                return reg
        return None

    def search_cases(self, keyword: str = None, case_type: str = None) -> list[TypicalCase]:
        """搜索案例"""
        results = list(self.cases.values())

        if keyword:
            keyword_lower = keyword.lower()
            results = [
                c for c in results
                if keyword_lower in c.title.lower()
                or keyword_lower in c.description.lower()
                or keyword_lower in c.violation.lower()
            ]

        if case_type:
            results = [c for c in results if c.case_type == case_type]

        return results

    def search_faqs(self, query: str = None, category: str = None) -> list[FAQ]:
        """搜索FAQ"""
        results = self.faqs

        if query:
            query_lower = query.lower()
            results = [
                f for f in results
                if query_lower in f.question.lower()
                or query_lower in f.answer.lower()
            ]

        if category:
            results = [f for f in results if f.category == category]

        return results

    def get_compliance_requirements(self, category: str) -> list[str]:
        """获取合规要求"""
        requirements = []

        for reg in self.regulations.values():
            if reg.category == category:
                requirements.extend(reg.keywords)

        return list(set(requirements))

    def add_regulation(self, regulation: Regulation) -> None:
        """添加法规"""
        self.regulations[regulation.id] = regulation

    def add_case(self, case: TypicalCase) -> None:
        """添加案例"""
        self.cases[case.case_id] = case

    def add_faq(self, faq: FAQ) -> None:
        """添加FAQ"""
        self.faqs.append(faq)

    def export_to_file(self, output_dir: str = None) -> None:
        """导出到文件"""
        output_dir = output_dir or self.base_dir
        os.makedirs(output_dir, exist_ok=True)

        regulations_data = {
            "regulations": [vars(r) for r in self.regulations.values()]
        }
        with open(os.path.join(output_dir, "regulations.json"), "w", encoding="utf-8") as f:
            json.dump(regulations_data, f, ensure_ascii=False, indent=2)

        cases_data = {
            "cases": [vars(c) for c in self.cases.values()]
        }
        with open(os.path.join(output_dir, "cases.json"), "w", encoding="utf-8") as f:
            json.dump(cases_data, f, ensure_ascii=False, indent=2)

        faqs_data = {
            "faqs": [vars(f) for f in self.faqs]
        }
        with open(os.path.join(output_dir, "faqs.json"), "w", encoding="utf-8") as f:
            json.dump(faqs_data, f, ensure_ascii=False, indent=2)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "total_regulations": len(self.regulations),
            "total_cases": len(self.cases),
            "total_faqs": len(self.faqs),
            "by_category": {
                cat: sum(1 for r in self.regulations.values() if r.category == cat)
                for cat in set(r.category for r in self.regulations.values())
            },
        }
