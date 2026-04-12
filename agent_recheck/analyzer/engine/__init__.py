# -*- coding: utf-8 -*-
"""
分析引擎模块

包含：
- 规则加载器
- 规则匹配器
- 规则管理器
- 混合分析引擎
- 本地化规则引擎
- 评分标准解析器
"""

from .rule_loader import RuleLoader
from .matcher import RuleMatcher, MatchResult
from .rule_manager import RuleManager
from .hybrid_engine import HybridEngine, AnalysisResult
from .local_rules import LocalRuleEngine, RegionDetector
from .scoring_parser import ScoringParser, ScoringStandard, ScoringItem, ScoreType

__all__ = [
    # 规则加载
    'RuleLoader',
    # 规则匹配
    'RuleMatcher',
    'MatchResult',
    # 规则管理
    'RuleManager',
    # 混合分析
    'HybridEngine',
    'AnalysisResult',
    # 本地化规则
    'LocalRuleEngine',
    'RegionDetector',
    # 评分解析
    'ScoringParser',
    'ScoringStandard',
    'ScoringItem',
    'ScoreType',
]
