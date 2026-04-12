"""问题/风险点数据模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class IssueLocation(BaseModel):
    """问题位置"""
    chapter: Optional[str] = None
    section: Optional[str] = None
    article: Optional[str] = None
    paragraph: Optional[str] = None
    page: Optional[int] = None
    line_start: int
    line_end: int
    table_index: Optional[int] = None


class IssueEvidence(BaseModel):
    """问题证据"""
    quote: str
    location: IssueLocation
    highlight: Optional[str] = None
    context: Optional[str] = None


class IssueRule(BaseModel):
    """触发规则"""
    id: str
    name: str
    reference: str
    full_text: Optional[str] = None


class IssueSuggestion(BaseModel):
    """修改建议"""
    content: str
    original: Optional[str] = None


class Issue(BaseModel):
    """问题/风险点模型"""
    id: str
    type: str  # "规则匹配", "LLM识别"
    category: str
    level: str  # "critical", "high", "medium", "low"
    title: str
    description: Optional[str] = None

    evidence: IssueEvidence
    rule: IssueRule
    suggestion: IssueSuggestion

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "rule"  # "rule" or "llm"

    detected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
