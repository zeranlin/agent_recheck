"""指标追踪器"""

from datetime import datetime
from typing import Optional
from collections import defaultdict

from utils.logging import get_logger

logger = get_logger("tracker.metrics")


class MetricsTracker:
    """关键指标追踪"""

    def __init__(self):
        self.metrics: dict[str, int] = defaultdict(int)
        self.durations: dict[str, list] = defaultdict(list)

    def increment(self, metric: str, value: int = 1):
        """递增指标"""
        self.metrics[metric] += value
        logger.debug("metric_incremented", metric=metric, value=value)

    def record_duration(self, metric: str, duration_ms: int):
        """记录耗时"""
        self.durations[metric].append(duration_ms)

    def get_metric(self, metric: str) -> int:
        """获取指标值"""
        return self.metrics.get(metric, 0)

    def get_all_metrics(self) -> dict:
        """获取所有指标"""
        result = dict(self.metrics)

        # 添加平均值
        for metric, durations in self.durations.items():
            if durations:
                result[f"{metric}_avg_ms"] = sum(durations) / len(durations)

        return result

    def reset(self):
        """重置所有指标"""
        self.metrics.clear()
        self.durations.clear()
        logger.info("metrics_reset")
