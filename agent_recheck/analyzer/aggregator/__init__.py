# -*- coding: utf-8 -*-
"""
结果聚合模块

包含：
- 智能去重
- 多源结果合并
- 批量分析聚合
"""

from .merger import IssueAggregator, BatchAggregator, MergeConfig

__all__ = [
    'IssueAggregator',
    'BatchAggregator',
    'MergeConfig',
]
