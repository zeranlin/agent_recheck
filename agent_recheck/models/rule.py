"""规则数据模型"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """风险等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleCategory(str, Enum):
    """规则类别"""
    DISCRIMINATION = "非歧视性"           # 非歧视性审查
    PROCUREMENT = "采购需求"             # 采购需求合规性
    SCORING = "评分标准"                 # 评分标准合规性
    CONTRACT = "合同条款"                 # 合同条款风险
    CONSISTENCY = "一致性"               # 一致性审查
    POLICY = "政策落实"                  # 政策落实审查
    CERTIFICATION = "认证证书"            # 认证证书规则


class PatternMatch(BaseModel):
    """匹配模式"""
    type: str  # regex, keyword, composite
    match: list[str] = []
    exclude_context: list[str] = []
    conditions: Optional[dict] = None


class RuleReference(BaseModel):
    """法规依据"""
    law: str
    article: str
    full_text: Optional[str] = None
    url: Optional[str] = None


class RuleSuggestion(BaseModel):
    """修改建议模板"""
    template: str
    example: Optional[str] = None


class Rule(BaseModel):
    """规则模型"""
    id: str
    name: str
    category: RuleCategory
    level: RiskLevel
    severity: str = "default"

    pattern: PatternMatch
    reference: RuleReference
    suggestion: RuleSuggestion

    enabled: bool = True
    version: str = "1.0"
    tags: list[str] = []

    class Config:
        use_enum_values = True


class RuleMatchResult(BaseModel):
    """规则匹配结果"""
    rule: Rule
    matched: bool
    confidence: float = 0.0
    matched_text: Optional[str] = None
    location: Optional[dict] = None
