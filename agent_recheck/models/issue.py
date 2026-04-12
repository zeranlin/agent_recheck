# -*- coding: utf-8 -*-
"""
问题数据模型
"""

from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IssueLevel(Enum):
    """问题级别"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class IssueLocation:
    """问题位置"""
    page: int = 0
    line: int = 0
    section: str = ""
    start: int = 0
    end: int = 0
    context: str = ""


@dataclass
class IssueEvidence:
    """问题证据"""
    text: str = ""
    type: str = ""  # original/matched/calculated
    confidence: float = 0.0


@dataclass
class IssueRule:
    """触发规则"""
    rule_id: str = ""
    rule_name: str = ""
    category: str = ""
    severity: str = ""


@dataclass
class IssueSuggestion:
    """修改建议"""
    type: str = ""  # remove/modify/add
    original: str = ""
    suggested: str = ""
    reason: str = ""


@dataclass
class Issue:
    """审查问题"""
    issue_id: str = ""
    title: str = ""
    description: str = ""
    level: IssueLevel = IssueLevel.MEDIUM
    category: str = ""
    location: IssueLocation = field(default_factory=IssueLocation)
    evidence: List[IssueEvidence] = field(default_factory=list)
    rule: Optional[IssueRule] = None
    suggestion: Optional[IssueSuggestion] = None
    confidence: float = 0.0
    source: str = ""  # rule/llm/manual
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
