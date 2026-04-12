# -*- coding: utf-8 -*-
"""
准确性评估框架

用于评估规则和 LLM 的准确性：
1. Precision / Recall / F1
2. 混淆矩阵
3. 阈值敏感性分析
4. 定期评估报告
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os

from ..analyzer.engine.matcher import MatchResult, Issue
from ..analyzer.llm.client import LLMClient


class MetricType(Enum):
    """指标类型"""
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    ACCURACY = "accuracy"


@dataclass
class Annotation:
    """标注数据"""
    issue_id: str
    text: str
    start_pos: int
    end_pos: int
    category: str
    severity: str
    is_true_positive: bool
    notes: str = ""
    annotated_by: str = ""
    annotated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EvaluationResult:
    """评估结果"""
    metric_type: MetricType
    value: float
    confidence_interval: tuple[float, float] = (0.0, 1.0)
    sample_size: int = 0


@dataclass
class ConfusionMatrix:
    """混淆矩阵"""
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        tp = self.true_positives
        fp = self.false_positives
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        tp = self.true_positives
        fn = self.false_negatives
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p = self.precision
        r = self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        tp = self.true_positives
        tn = self.true_negatives
        fp = self.false_positives
        fn = self.false_negatives
        total = tp + tn + fp + fn
        return (tp + tn) / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
        }


@dataclass
class TestCase:
    """测试用例"""
    case_id: str
    document_name: str
    document_path: str
    expected_issues: list[Annotation] = field(default_factory=list)
    predicted_issues: list[Issue] = field(default_factory=list)
    confusion_matrix: Optional[ConfusionMatrix] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_confusion_matrix(self) -> ConfusionMatrix:
        """计算混淆矩阵"""
        cm = ConfusionMatrix()

        expected_set = {
            (i.start_pos, i.end_pos, i.category) for i in self.expected_issues
        }
        predicted_set = {
            (p.location.get("start", 0), p.location.get("end", 0), p.rule_id.split("-")[0])
            for p in self.predicted_issues
        }

        for exp in expected_set:
            if exp in predicted_set:
                cm.true_positives += 1
            else:
                cm.false_negatives += 1

        for pred in predicted_set:
            if pred not in expected_set:
                cm.false_positives += 1

        return cm


@dataclass
class EvaluationReport:
    """评估报告"""
    report_id: str
    created_at: datetime = field(default_factory=datetime.now)
    test_cases: list[TestCase] = field(default_factory=list)
    overall_confusion_matrix: Optional[ConfusionMatrix] = None
    metrics: dict[str, float] = field(default_factory=dict)
    by_category: dict[str, dict] = field(default_factory=dict)
    by_severity: dict[str, dict] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_metrics(self) -> dict:
        """计算整体指标"""
        if not self.test_cases:
            return {}

        overall_cm = ConfusionMatrix()
        for tc in self.test_cases:
            if tc.confusion_matrix is None:
                tc.confusion_matrix = tc.compute_confusion_matrix()
            cm = tc.confusion_matrix
            overall_cm.true_positives += cm.true_positives
            overall_cm.false_positives += cm.false_positives
            overall_cm.true_negatives += cm.true_negatives
            overall_cm.false_negatives += cm.false_negatives

        self.overall_confusion_matrix = overall_cm

        self.metrics = {
            "precision": overall_cm.precision,
            "recall": overall_cm.recall,
            "f1": overall_cm.f1,
            "accuracy": overall_cm.accuracy,
            "total_test_cases": len(self.test_cases),
            "total_expected_issues": sum(len(tc.expected_issues) for tc in self.test_cases),
            "total_predicted_issues": sum(len(tc.predicted_issues) for tc in self.test_cases),
        }

        self._compute_by_category()
        self._compute_by_severity()

        return self.metrics

    def _compute_by_category(self) -> None:
        """按类别计算"""
        categories = {}
        for tc in self.test_cases:
            for exp in tc.expected_issues:
                cat = exp.category
                if cat not in categories:
                    categories[cat] = {"expected": [], "predicted": []}
                categories[cat]["expected"].append(exp)

            for pred in tc.predicted_issues:
                cat = pred.rule_id.split("-")[0]
                if cat not in categories:
                    categories[cat] = {"expected": [], "predicted": []}
                categories[cat]["predicted"].append(pred)

        for cat, data in categories.items():
            cm = ConfusionMatrix()
            exp_set = {(e.start_pos, e.end_pos) for e in data["expected"]}
            pred_set = {(p.location.get("start", 0), p.location.get("end", 0)) for p in data["predicted"]}

            cm.true_positives = len(exp_set & pred_set)
            cm.false_negatives = len(exp_set - pred_set)
            cm.false_positives = len(pred_set - exp_set)

            self.by_category[cat] = cm.to_dict()

    def _compute_by_severity(self) -> None:
        """按严重程度计算"""
        severities = {}
        for tc in self.test_cases:
            for exp in tc.expected_issues:
                sev = exp.severity
                if sev not in severities:
                    severities[sev] = {"expected": [], "predicted": []}
                severities[sev]["expected"].append(exp)

            for pred in tc.predicted_issues:
                sev = pred.severity.value if hasattr(pred.severity, 'value') else "low"
                if sev not in severities:
                    severities[sev] = {"expected": [], "predicted": []}
                severities[sev]["predicted"].append(pred)

        for sev, data in severities.items():
            cm = ConfusionMatrix()
            exp_set = {(e.start_pos, e.end_pos) for e in data["expected"]}
            pred_set = {(p.location.get("start", 0), p.location.get("end", 0)) for p in data["predicted"]}

            cm.true_positives = len(exp_set & pred_set)
            cm.false_negatives = len(exp_set - pred_set)
            cm.false_positives = len(pred_set - exp_set)

            self.by_severity[sev] = cm.to_dict()

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at.isoformat(),
            "metrics": self.metrics,
            "overall_confusion_matrix": self.overall_confusion_matrix.to_dict() if self.overall_confusion_matrix else {},
            "by_category": self.by_category,
            "by_severity": self.by_severity,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class AccuracyEvaluator:
    """准确性评估器"""

    def __init__(self, test_data_dir: str = None):
        self.test_data_dir = test_data_dir or "./tests/fixtures"
        self.test_cases: list[TestCase] = []
        self.reports: list[EvaluationReport] = []

    def load_test_cases(self, test_data_dir: str = None) -> list[TestCase]:
        """加载测试用例"""
        test_dir = test_data_dir or self.test_data_dir
        if not os.path.exists(test_dir):
            return []

        test_cases = []
        for filename in os.listdir(test_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(test_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tc = self._parse_test_case(data)
                    test_cases.append(tc)

        self.test_cases = test_cases
        return test_cases

    def _parse_test_case(self, data: dict) -> TestCase:
        """解析测试用例"""
        expected = [
            Annotation(
                issue_id=a["issue_id"],
                text=a["text"],
                start_pos=a.get("start_pos", 0),
                end_pos=a.get("end_pos", 0),
                category=a["category"],
                severity=a["severity"],
                is_true_positive=a.get("is_true_positive", True),
                notes=a.get("notes", ""),
            )
            for a in data.get("expected_issues", [])
        ]

        return TestCase(
            case_id=data["case_id"],
            document_name=data["document_name"],
            document_path=data["document_path"],
            expected_issues=expected,
            metadata=data.get("metadata", {}),
        )

    def add_test_case(self, test_case: TestCase) -> None:
        """添加测试用例"""
        self.test_cases.append(test_case)

    def add_annotation(self, case_id: str, annotation: Annotation) -> None:
        """添加标注"""
        for tc in self.test_cases:
            if tc.case_id == case_id:
                tc.expected_issues.append(annotation)
                return
        raise ValueError(f"Test case not found: {case_id}")

    def run_evaluation(self, run_id: str = None) -> EvaluationReport:
        """运行评估"""
        report = EvaluationReport(
            report_id=run_id or f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            test_cases=self.test_cases,
        )

        for tc in self.test_cases:
            tc.confusion_matrix = tc.compute_confusion_matrix()

        report.compute_metrics()
        self.reports.append(report)
        return report

    def threshold_analysis(
        self,
        thresholds: list[float] = None,
    ) -> dict[float, dict]:
        """阈值敏感性分析"""
        if thresholds is None:
            thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]

        results = {}
        for threshold in thresholds:
            filtered_cases = []
            for tc in self.test_cases:
                tc_copy = TestCase(
                    case_id=tc.case_id,
                    document_name=tc.document_name,
                    document_path=tc.document_path,
                    expected_issues=tc.expected_issues,
                    predicted_issues=[
                        p for p in tc.predicted_issues
                        if (p.confidence or 0.5) >= threshold
                    ],
                    metadata=tc.metadata,
                )
                filtered_cases.append(tc_copy)

            cm = ConfusionMatrix()
            for tc in filtered_cases:
                tc.confusion_matrix = tc.compute_confusion_matrix()
                cm.true_positives += tc.confusion_matrix.true_positives
                cm.false_positives += tc.confusion_matrix.false_positives
                cm.true_negatives += tc.confusion_matrix.true_negatives
                cm.false_negatives += tc.confusion_matrix.false_negatives

            results[threshold] = cm.to_dict()

        return results

    def save_report(self, report: EvaluationReport, output_dir: str = None) -> str:
        """保存评估报告"""
        output_dir = output_dir or f"./reports/evaluation"
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, f"{report.report_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.to_json())

        return filepath

    def get_latest_report(self) -> Optional[EvaluationReport]:
        """获取最新报告"""
        return self.reports[-1] if self.reports else None

    def compare_reports(self, report_id1: str, report_id2: str) -> dict:
        """比较两个报告"""
        r1 = next((r for r in self.reports if r.report_id == report_id1), None)
        r2 = next((r for r in self.reports if r.report_id == report_id2), None)

        if not r1 or not r2:
            raise ValueError("Report not found")

        return {
            "report1": r1.metrics,
            "report2": r2.metrics,
            "delta": {
                k: round(r2.metrics.get(k, 0) - r1.metrics.get(k, 0), 4)
                for k in ["precision", "recall", "f1"]
            },
        }


class PeriodicEvaluator:
    """定期评估器"""

    def __init__(self, evaluator: AccuracyEvaluator = None):
        self.evaluator = evaluator or AccuracyEvaluator()
        self.schedule: dict = {}
        self.last_evaluation: Optional[datetime] = None

    def set_schedule(self, frequency: str, time: str = "09:00") -> None:
        """设置评估计划"""
        self.schedule = {
            "frequency": frequency,
            "time": time,
        }

    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.last_evaluation:
            return True

        from datetime import timedelta

        freq = self.schedule.get("frequency", "weekly")
        now = datetime.now()
        elapsed = now - self.last_evaluation

        if freq == "daily":
            return elapsed >= timedelta(days=1)
        elif freq == "weekly":
            return elapsed >= timedelta(weeks=1)
        elif freq == "monthly":
            return elapsed >= timedelta(days=30)

        return False

    def run_and_save(self, output_dir: str = None) -> EvaluationReport:
        """运行并保存"""
        report = self.evaluator.run_evaluation()
        filepath = self.evaluator.save_report(report, output_dir)
        self.last_evaluation = datetime.now()
        return report


class RuleMetrics:
    """规则质量指标"""

    def __init__(self):
        self.rule_stats: dict[str, dict] = {}

    def compute_rule_metrics(
        self,
        rule_id: str,
        true_positives: int,
        false_positives: int,
        false_negatives: int,
    ) -> dict:
        """计算单条规则指标"""
        cm = ConfusionMatrix(
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        )

        metrics = {
            "rule_id": rule_id,
            "precision": round(cm.precision, 4),
            "recall": round(cm.recall, 4),
            "f1": round(cm.f1, 4),
            "total_detections": true_positives + false_positives,
            "missed_detections": false_negatives,
            "false_alarms": false_positives,
        }

        self.rule_stats[rule_id] = metrics
        return metrics

    def get_weak_rules(self, threshold: float = 0.7) -> list[dict]:
        """获取弱规则"""
        weak = []
        for rule_id, stats in self.rule_stats.items():
            if stats["f1"] < threshold:
                weak.append(stats)
        return sorted(weak, key=lambda x: x["f1"])

    def get_strong_rules(self, threshold: float = 0.9) -> list[dict]:
        """获取强规则"""
        strong = []
        for rule_id, stats in self.rule_stats.items():
            if stats["f1"] >= threshold:
                strong.append(stats)
        return sorted(strong, key=lambda x: x["f1"], reverse=True)

    def recommend_rules_to_improve(self, top_n: int = 5) -> list[dict]:
        """推荐需要改进的规则"""
        weak = self.get_weak_rules()
        recommendations = []

        for rule_stat in weak[:top_n]:
            rec = {
                "rule_id": rule_stat["rule_id"],
                "current_f1": rule_stat["f1"],
                "issues": [],
            }

            if rule_stat["recall"] < 0.8:
                rec["issues"].append(f"Recall过低 ({rule_stat['recall']:.2f})，需要扩展 patterns")
            if rule_stat["precision"] < 0.8:
                rec["issues"].append(f"Precision过低 ({rule_stat['precision']:.2f})，存在误报")

            recommendations.append(rec)

        return recommendations
