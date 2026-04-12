# -*- coding: utf-8 -*-
"""
评估模块

包含：
- 准确性评估框架
- 测试集标注工具
- 规则质量指标
- 定期评估器
"""

from .accuracy_evaluator import (
    AccuracyEvaluator,
    EvaluationReport,
    EvaluationResult,
    TestCase,
    ConfusionMatrix,
    Annotation,
    RuleMetrics,
    PeriodicEvaluator,
    MetricType,
)
from .annotation_tool import (
    AnnotationTool,
    BatchAnnotationTool,
    AnnotationStatus,
)

__all__ = [
    # 评估
    "AccuracyEvaluator",
    "EvaluationReport",
    "EvaluationResult",
    "TestCase",
    "ConfusionMatrix",
    "Annotation",
    "RuleMetrics",
    "PeriodicEvaluator",
    "MetricType",
    # 标注
    "AnnotationTool",
    "BatchAnnotationTool",
    "AnnotationStatus",
]
