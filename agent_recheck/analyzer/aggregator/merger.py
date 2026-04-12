# -*- coding: utf-8 -*-
"""
结果聚合器

合并多个分析结果：
- 多源结果合并
- 智能去重
- 优先级排序
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

from models.issue import Issue, IssueLevel


@dataclass
class MergeConfig:
    """合并配置"""
    # 去重策略
    dedup_by: str = "semantic"  # exact, keyword, semantic
    dedup_threshold: float = 0.8  # 相似度阈值
    
    # 置信度策略
    confidence_strategy: str = "max"  # max, weighted, average
    
    # 优先级策略
    priority_by: str = "level"  # level, confidence, source
    
    # 来源权重
    source_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.source_weights is None:
            self.source_weights = {
                "llm": 0.9,
                "llm+rule": 0.95,
                "rule": 0.8,
                "fallback": 0.6,
                "heuristic": 0.5,
            }


class IssueAggregator:
    """
    问题聚合器
    
    功能：
    - 多源结果合并
    - 智能去重
    - 置信度计算
    - 优先级排序
    """
    
    def __init__(self, config: Optional[MergeConfig] = None):
        self.config = config or MergeConfig()
        self._merged_issues: List[Issue] = []
    
    def aggregate(
        self,
        issues_lists: List[List[Issue]],
    ) -> List[Issue]:
        """
        聚合多个问题列表
        
        Args:
            issues_lists: 多个来源的问题列表
            
        Returns:
            聚合后的问题列表
        """
        # 合并所有问题
        all_issues = []
        for issues in issues_lists:
            all_issues.extend(issues)
        
        if not all_issues:
            return []
        
        # 去重
        deduplicated = self._deduplicate(all_issues)
        
        # 计算置信度
        with_confidence = self._calculate_confidence(deduplicated)
        
        # 排序
        sorted_issues = self._sort(with_confidence)
        
        self._merged_issues = sorted_issues
        return sorted_issues
    
    def _deduplicate(self, issues: List[Issue]) -> List[Issue]:
        """去重"""
        if self.config.dedup_by == "exact":
            return self._deduplicate_exact(issues)
        elif self.config.dedup_by == "keyword":
            return self._deduplicate_keyword(issues)
        else:  # semantic
            return self._deduplicate_semantic(issues)
    
    def _deduplicate_exact(self, issues: List[Issue]) -> List[Issue]:
        """精确去重"""
        seen = set()
        unique = []
        
        for issue in issues:
            key = self._exact_key(issue)
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        
        return unique
    
    def _exact_key(self, issue: Issue) -> str:
        """生成精确键"""
        return hashlib.md5(
            f"{issue.category}_{issue.level}_{issue.title}".encode()
        ).hexdigest()
    
    def _deduplicate_keyword(self, issues: List[Issue]) -> List[Issue]:
        """基于关键词去重"""
        groups = defaultdict(list)
        
        for issue in issues:
            key = self._keyword_key(issue)
            groups[key].append(issue)
        
        # 保留置信度最高的
        unique = []
        for key, group in groups.items():
            best = max(group, key=lambda x: x.confidence)
            unique.append(best)
        
        return unique
    
    def _keyword_key(self, issue: Issue) -> str:
        """生成关键词键"""
        # 提取关键词
        keywords = []
        
        if issue.evidence and issue.evidence.highlight:
            keywords.append(issue.evidence.highlight)
        
        if issue.title:
            keywords.append(issue.title[:30])
        
        keywords.sort()
        return "|".join(keywords)
    
    def _deduplicate_semantic(self, issues: List[Issue]) -> List[Issue]:
        """语义去重"""
        clusters = []
        
        for issue in issues:
            # 找到相似的簇
            found_cluster = None
            for cluster in clusters:
                representative = cluster[0]
                if self._is_similar(issue, representative, self.config.dedup_threshold):
                    cluster.append(issue)
                    found_cluster = cluster
                    break
            
            if found_cluster is None:
                clusters.append([issue])
        
        # 从每个簇中选择最佳代表
        unique = []
        for cluster in clusters:
            best = self._select_best_from_cluster(cluster)
            unique.append(best)
        
        return unique
    
    def _is_similar(
        self, 
        issue1: Issue, 
        issue2: Issue, 
        threshold: float
    ) -> bool:
        """判断两个问题是否相似"""
        # 类别必须相同
        if issue1.category != issue2.category:
            return False
        
        # 级别必须相同
        if issue1.level != issue2.level:
            return False
        
        # 检查关键词重叠
        key1 = self._keyword_key(issue1)
        key2 = self._keyword_key(issue2)
        
        keywords1 = set(key1.split("|"))
        keywords2 = set(key2.split("|"))
        
        if not keywords1 or not keywords2:
            return False
        
        overlap = len(keywords1 & keywords2) / len(keywords1 | keywords2)
        return overlap >= threshold
    
    def _select_best_from_cluster(self, cluster: List[Issue]) -> Issue:
        """从簇中选择最佳问题"""
        # 优先级：来源权重 > 置信度 > 标题长度
        best = cluster[0]
        best_score = self._issue_score(best)
        
        for issue in cluster[1:]:
            score = self._issue_score(issue)
            if score > best_score:
                best = issue
                best_score = score
        
        return best
    
    def _issue_score(self, issue: Issue) -> float:
        """计算问题得分"""
        # 来源权重
        source_weight = self.config.source_weights.get(issue.source, 0.5)
        
        # 置信度
        confidence = issue.confidence
        
        # 综合得分
        return source_weight * 0.4 + confidence * 0.6
    
    def _calculate_confidence(self, issues: List[Issue]) -> List[Issue]:
        """计算置信度"""
        for issue in issues:
            # 调整置信度
            source_weight = self.config.source_weights.get(issue.source, 0.5)
            issue.confidence = issue.confidence * source_weight
        
        return issues
    
    def _sort(self, issues: List[Issue]) -> List[Issue]:
        """排序"""
        if self.config.priority_by == "level":
            # 按级别排序：高 -> 中 -> 低
            level_order = {"high": 0, "medium": 1, "low": 2, None: 3}
            return sorted(
                issues, 
                key=lambda x: (level_order.get(x.level, 3), -x.confidence)
            )
        elif self.config.priority_by == "confidence":
            return sorted(issues, key=lambda x: -x.confidence)
        else:  # source
            source_order = {"llm+rule": 0, "llm": 1, "rule": 2, "fallback": 3}
            return sorted(
                issues, 
                key=lambda x: (source_order.get(x.source, 99), -x.confidence)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._merged_issues:
            return {"total": 0}
        
        return {
            "total": len(self._merged_issues),
            "by_level": {
                "high": sum(1 for i in self._merged_issues if i.level == "high"),
                "medium": sum(1 for i in self._merged_issues if i.level == "medium"),
                "low": sum(1 for i in self._merged_issues if i.level == "low"),
            },
            "by_source": {
                src: sum(1 for i in self._merged_issues if i.source == src)
                for src in set(i.source for i in self._merged_issues)
            },
            "by_category": {
                cat: sum(1 for i in self._merged_issues if i.category == cat)
                for cat in set(i.category for i in self._merged_issues if i.category)
            },
        }


class BatchAggregator:
    """
    批量聚合器
    
    用于批量分析多个文档后的结果聚合
    """
    
    def __init__(self, aggregator: Optional[IssueAggregator] = None):
        self.aggregator = aggregator or IssueAggregator()
        self._all_issues: List[Issue] = []
        self._by_document: Dict[str, List[Issue]] = {}
    
    def add_document_results(
        self, 
        document_id: str, 
        issues: List[Issue]
    ):
        """添加单个文档的结果"""
        self._by_document[document_id] = issues
        self._all_issues.extend(issues)
    
    def aggregate_all(self) -> List[Issue]:
        """聚合所有文档结果"""
        return self.aggregator.aggregate([self._all_issues])
    
    def get_by_document(self) -> Dict[str, List[Issue]]:
        """获取按文档分组的结果"""
        return self._by_document.copy()
    
    def get_cross_document_issues(self) -> List[Issue]:
        """获取跨文档的共性问题"""
        # 按类别和级别分组
        groups = defaultdict(list)
        
        for issue in self._all_issues:
            key = f"{issue.category}_{issue.level}"
            groups[key].append(issue)
        
        # 找出出现多次的问题
        cross_issues = []
        for key, issues in groups.items():
            if len(issues) > 1:
                # 选择最佳代表
                best = max(issues, key=lambda x: x.confidence)
                best._duplicate_count = len(issues)
                cross_issues.append(best)
        
        return cross_issues


# 导出
__all__ = [
    'IssueAggregator',
    'BatchAggregator',
    'MergeConfig',
]
