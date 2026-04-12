"""准确性评估器"""

import json
from pathlib import Path
from typing import Optional

from models.issue import Issue
from utils.logging import get_logger

logger = get_logger("evaluator.accuracy")


class AccuracyEvaluator:
    """审查准确性评估"""

    def __init__(self):
        pass

    def evaluate(self, test_set_path: Path) -> dict:
        """
        评估准确性

        Args:
            test_set_path: 测试集路径

        Returns:
            评估指标
        """
        # 加载测试集
        test_cases = self._load_test_cases(test_set_path)

        if not test_cases:
            logger.warning("no_test_cases_found", path=str(test_set_path))
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "false_positive_rate": 0.0,
            }

        # 计算指标
        total_tp = 0  # True Positive
        total_fp = 0  # False Positive
        total_fn = 0  # False Negative

        for test_case in test_cases:
            predicted = test_case.get("predicted_issues", [])
            ground_truth = test_case.get("ground_truth_issues", [])

            tp, fp, fn = self._calculate_case_metrics(predicted, ground_truth)
            total_tp += tp
            total_fp += fp
            total_fn += fn

        # 计算总体指标
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        fpr = total_fp / (total_fp + total_tp) if (total_fp + total_tp) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "false_positive_rate": fpr,
            "test_cases_count": len(test_cases),
        }

    def generate_report(self, metrics: dict, output: Path):
        """生成评估报告"""
        report_lines = [
            "# 准确性评估报告",
            "",
            "## 总体指标",
            f"- Precision（准确率）: {metrics['precision']:.1%}",
            f"- Recall（召回率）: {metrics['recall']:.1%}",
            f"- F1 Score: {metrics['f1_score']:.1%}",
            f"- 误报率: {metrics['false_positive_rate']:.1%}",
            f"- 测试用例数: {metrics['test_cases_count']}",
            "",
            "## 达标情况",
            f"- Precision ≥ 85%: {'✓' if metrics['precision'] >= 0.85 else '✗'}",
            f"- Recall ≥ 90%: {'✓' if metrics['recall'] >= 0.90 else '✗'}",
        ]

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        logger.info("evaluation_report_saved", output=str(output))

    def _load_test_cases(self, test_set_path: Path) -> list[dict]:
        """加载测试用例"""
        test_cases = []

        # 查找所有带标注的测试文件
        for issues_file in test_set_path.rglob("issues.json"):
            predicted_file = issues_file.parent / f"{issues_file.stem}_predicted.json"

            test_case = {
                "ground_truth_issues": self._load_json(issues_file),
                "predicted_issues": self._load_json(predicted_file) if predicted_file.exists() else [],
            }

            test_cases.append(test_case)

        return test_cases

    def _load_json(self, path: Path) -> list:
        """加载 JSON 文件"""
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("json_load_failed", path=str(path), error=str(e))
            return []

    def _calculate_case_metrics(self, predicted: list, ground_truth: list) -> tuple:
        """计算单个测试用例的指标"""
        tp = 0
        fp = 0
        fn = 0

        # 简化的匹配：基于标题和类别
        matched_gt = set()

        for pred in predicted:
            pred_key = (pred.get("title", ""), pred.get("category", ""))

            for i, gt in enumerate(ground_truth):
                if i in matched_gt:
                    continue

                gt_key = (gt.get("title", ""), gt.get("category", ""))

                if pred_key == gt_key or pred_key[1] == gt_key[1]:
                    tp += 1
                    matched_gt.add(i)
                    break
            else:
                fp += 1

        fn = len(ground_truth) - len(matched_gt)

        return tp, fp, fn
