"""Token 消耗追踪器"""

from datetime import datetime
from typing import Optional
from collections import defaultdict

from utils.logging import get_logger

logger = get_logger("tracker.token")


class TokenTracker:
    """Token 消耗追踪"""

    def __init__(self):
        self.usage: dict[str, list] = defaultdict(list)
        self.total_consumed: int = 0

    def track(self, operation: str, tokens: int):
        """
        记录 Token 消耗

        Args:
            operation: 操作类型 (analyze/learn/consistency_check)
            tokens: 消耗数量
        """
        self.usage[operation].append({
            "tokens": tokens,
            "timestamp": datetime.now().isoformat(),
        })
        self.total_consumed += tokens

        logger.debug("token_tracked", operation=operation, tokens=tokens)

    def get_consumption_report(self) -> dict:
        """生成消耗报告"""
        report = {
            "total": self.total_consumed,
            "by_operation": {},
        }

        for operation, records in self.usage.items():
            total = sum(r["tokens"] for r in records)
            report["by_operation"][operation] = {
                "count": len(records),
                "total_tokens": total,
                "avg_tokens": total / len(records) if records else 0,
            }

        return report

    def check_quota(self, quota: int) -> bool:
        """检查是否超配额"""
        return self.total_consumed >= quota

    def get_remaining(self, quota: int) -> int:
        """获取剩余配额"""
        return max(0, quota - self.total_consumed)
