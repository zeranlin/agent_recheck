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
    type: str = ""  # keyword/regex/composite
    match: List[str] = field(default_factory=list)  # 匹配模式列表
    exclude_context: List[str] = field(default_factory=list)  # 排除上下文
    matched_text: str = ""
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 0.0


@dataclass
class RuleReference:
    """规则引用"""
    law: str = ""  # 法规名称
    article: str = ""  # 条款编号
    full_text: str = ""  # 法规原文
    regulation: str = ""  # 兼容旧字段
    description: str = ""  # 兼容旧字段


@dataclass
class RuleSuggestion:
    """规则建议"""
    template: str = ""  # 修改建议模板
    example: str = ""  # 修改示例
    type: str = ""  # remove/modify/add
    description: str = ""
    priority: int = 0


@dataclass
class Rule:
    """审查规则"""
    id: str = ""
    name: str = ""
    category: str = ""  # 歧视性/采购需求/评分标准/合同条款/认证证书
    severity: str = ""  # critical/high/medium/low
    description: str = ""
    pattern: Optional[PatternMatch] = None  # YAML 格式使用 pattern
    patterns: List[str] = field(default_factory=list)  # 兼容旧格式
    keywords: List[str] = field(default_factory=list)
    reference: Optional[RuleReference] = None  # YAML 格式使用单数
    references: List[RuleReference] = field(default_factory=list)  # 兼容旧格式
    suggestion: Optional[RuleSuggestion] = None  # YAML 格式使用单数
    suggestions: List[RuleSuggestion] = field(default_factory=list)  # 兼容旧格式
    legal_basis: str = ""  # 法律依据
    verification: Optional[dict] = None  # 验证配置
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
