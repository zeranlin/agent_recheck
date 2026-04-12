# -*- coding: utf-8 -*-
"""
规则数据模型
"""

from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RuleCategory(Enum):
    """规则类别"""
    DISCRIMINATION = "discrimination"       # 歧视性条款
    SCORING = "scoring"                     # 评分标准
    QUALIFICATION = "qualification"         # 资质要求
    PROCUREMENT = "procurement"            # 采购需求
    CONTRACT = "contract"                  # 合同条款
    CERTIFICATION = "certification"        # 认证证书
    FAIR_COMPETITION = "fair_competition"  # 公平竞争


class RiskLevel(Enum):
    """风险级别"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PatternMatch:
    """模式匹配结果"""
    pattern: str = ""
    matched_text: str = ""
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 0.0


@dataclass
class RuleReference:
    """规则引用"""
    regulation: str = ""
    article: str = ""
    description: str = ""


@dataclass
class RuleSuggestion:
    """规则建议"""
    type: str = ""  # remove/modify/add
    description: str = ""
    priority: int = 0


@dataclass
class Rule:
    """审查规则"""
    id: str = ""
    name: str = ""
    category: str = ""
    severity: str = ""
    description: str = ""
    patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    references: List[RuleReference] = field(default_factory=list)
    suggestions: List[RuleSuggestion] = field(default_factory=list)
    enabled: bool = True
    confidence_threshold: float = 0.7
    tags: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class RuleMatchResult:
    """规则匹配结果"""
    rule_id: str = ""
    rule_name: str = ""
    matched: bool = False
    matches: List[PatternMatch] = field(default_factory=list)
    confidence: float = 0.0
    location: dict = field(default_factory=dict)
