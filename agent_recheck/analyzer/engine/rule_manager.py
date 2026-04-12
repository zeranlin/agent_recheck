"""规则管理器"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from models.rule import Rule
from utils.logging import get_logger

logger = get_logger("engine.rule_manager")


class RuleManager:
    """规则生命周期管理"""

    def __init__(self, rules_dir: Optional[Path] = None):
        self.rules_dir = rules_dir or Path("rules")
        self.version_history: dict[str, list] = {}

    def register_rule(self, rule: Rule, approved: bool = False) -> bool:
        """
        注册规则

        Args:
            rule: 规则
            approved: 是否已审批

        Returns:
            是否成功
        """
        if not approved:
            logger.warning("rule_not_approved", rule_id=rule.id)
            # 进入审核队列
            return self._add_to_review_queue(rule)

        # 验证规则格式
        if not self._validate_rule(rule):
            logger.error("rule_validation_failed", rule_id=rule.id)
            return False

        # 检测冲突
        conflicts = self.check_conflicts(rule)
        if conflicts:
            logger.warning("rule_conflicts_detected", rule_id=rule.id, conflicts=conflicts)

        # 保存规则
        return self._save_rule(rule)

    def deprecate_rule(self, rule_id: str, reason: str):
        """废弃规则"""
        rule_file = self._get_rule_file(rule_id)
        if not rule_file:
            logger.warning("rule_not_found", rule_id=rule_id)
            return False

        # 记录废弃信息
        self._record_deprecation(rule_id, reason)

        # 删除规则文件
        rule_file.unlink()
        logger.info("rule_deprecated", rule_id=rule_id, reason=reason)

        return True

    def rollback_rule(self, rule_id: str, version: str) -> bool:
        """回滚规则到指定版本"""
        history = self.version_history.get(rule_id, [])
        target_version = None

        for v in history:
            if v.get("version") == version:
                target_version = v
                break

        if not target_version:
            logger.error("version_not_found", rule_id=rule_id, version=version)
            return False

        # 恢复规则
        rule = Rule(**target_version["data"])
        return self._save_rule(rule)

    def check_conflicts(self, rule: Rule) -> list[dict]:
        """检测规则冲突"""
        conflicts = []

        # 加载现有规则
        from .rule_loader import RuleLoader
        loader = RuleLoader(self.rules_dir)
        existing_rules = loader.load_all()

        for existing in existing_rules:
            if existing.id == rule.id:
                continue

            # 检查类别和级别冲突
            if existing.category == rule.category:
                # 检查关键词重叠
                overlap = set(existing.pattern.match) & set(rule.pattern.match)
                if overlap:
                    conflicts.append({
                        "rule_id": existing.id,
                        "overlap": list(overlap),
                    })

        return conflicts

    def _validate_rule(self, rule: Rule) -> bool:
        """验证规则格式"""
        try:
            # 基本验证
            assert rule.id, "规则ID不能为空"
            assert rule.name, "规则名称不能为空"
            assert rule.pattern.match, "匹配模式不能为空"
            assert rule.reference.law, "法规依据不能为空"

            return True
        except AssertionError as e:
            logger.error("rule_validation_error", error=str(e))
            return False

    def _add_to_review_queue(self, rule: Rule) -> bool:
        """添加到审核队列"""
        queue_file = self.rules_dir / "_review_queue.yaml"
        queue = []

        if queue_file.exists():
            with open(queue_file, encoding="utf-8") as f:
                queue = yaml.safe_load(f) or []

        queue.append({
            "rule_id": rule.id,
            "name": rule.name,
            "submitted_at": datetime.now().isoformat(),
            "data": rule.model_dump(),
        })

        with open(queue_file, "w", encoding="utf-8") as f:
            yaml.dump(queue, f, allow_unicode=True)

        logger.info("rule_added_to_queue", rule_id=rule.id)
        return True

    def _save_rule(self, rule: Rule) -> bool:
        """保存规则"""
        category_dir = self.rules_dir / rule.category.value.lower()
        category_dir.mkdir(parents=True, exist_ok=True)

        rule_file = category_dir / f"{rule.id}.yaml"

        with open(rule_file, "w", encoding="utf-8") as f:
            yaml.dump(rule.model_dump(), f, allow_unicode=True, sort_keys=False)

        # 记录版本历史
        self._record_version(rule)

        logger.info("rule_saved", rule_id=rule.id, file=str(rule_file))
        return True

    def _record_version(self, rule: Rule):
        """记录版本"""
        if rule.id not in self.version_history:
            self.version_history[rule.id] = []

        self.version_history[rule.id].append({
            "version": rule.version,
            "updated_at": datetime.now().isoformat(),
            "data": rule.model_dump(),
        })

    def _record_deprecation(self, rule_id: str, reason: str):
        """记录废弃"""
        # 简化的废弃记录
        logger.info("rule_deprecation_recorded", rule_id=rule_id, reason=reason)

    def _get_rule_file(self, rule_id: str) -> Optional[Path]:
        """获取规则文件路径"""
        for category_dir in self.rules_dir.iterdir():
            if category_dir.is_dir():
                rule_file = category_dir / f"{rule_id}.yaml"
                if rule_file.exists():
                    return rule_file
        return None
