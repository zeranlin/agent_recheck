# -*- coding: utf-8 -*-
"""
分析引擎模块

包含：
- 文档解析器 (parser/)
- 规则引擎 (engine/)
- LLM 集成 (llm/)
- 结果聚合 (aggregator/)
- 一致性检查 (consistency.py)
- 审查工作流 (workflow.py)
"""

from .parser import (
    BaseParser,
    ParserFactory,
    DocxParser,
    PdfParser,
    EnhancedTableParser,
    ShenzhenAdapter,
)
from .engine import (
    RuleLoader,
    RuleMatcher,
    RuleManager,
    HybridEngine,
    AnalysisResult,
    LocalRuleEngine,
    ScoringParser,
    FallbackEngine,
)
from .llm import (
    LLMClient,
    PromptTemplates,
    LLMCache,
    StructuredOutputParser,
)
from .aggregator import IssueAggregator, BatchAggregator
from .consistency import ConsistencyChecker, ConsistencyResult, ConsistencyType
from .workflow import ReviewWorkflow, ReviewConfig, BatchReviewWorkflow, ReviewTask

__all__ = [
    # 解析器
    "BaseParser",
    "ParserFactory",
    "DocxParser",
    "PdfParser",
    "EnhancedTableParser",
    "ShenzhenAdapter",
    # 规则引擎
    "RuleLoader",
    "RuleMatcher",
    "RuleManager",
    "HybridEngine",
    "AnalysisResult",
    "LocalRuleEngine",
    "ScoringParser",
    "FallbackEngine",
    # LLM
    "LLMClient",
    "PromptTemplates",
    "LLMCache",
    "StructuredOutputParser",
    # 聚合
    "IssueAggregator",
    "BatchAggregator",
    # 一致性
    "ConsistencyChecker",
    "ConsistencyResult",
    "ConsistencyType",
    # 工作流
    "ReviewWorkflow",
    "ReviewConfig",
    "BatchReviewWorkflow",
    "ReviewTask",
]
