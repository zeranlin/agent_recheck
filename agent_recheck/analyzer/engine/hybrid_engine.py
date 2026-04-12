# -*- coding: utf-8 -*-
"""
混合分析引擎

整合规则引擎、LLM 和降级兜底机制，提供智能分析能力：
1. 混合模式：规则引擎 + LLM（默认）
2. 纯规则模式：仅使用规则引擎
3. 降级模式：规则引擎失败时使用启发式规则
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from ...models.document import Document, ParsedDocument
from ...models.report import AnalysisReport, ReportSummary
from ...models.issue import Issue, IssueLevel
from ...utils.logging import get_logger

from .rule_loader import RuleLoader
from .rule_manager import RuleManager
from .fallback_engine import FallbackEngine, GracefulDegradation, FallbackMode

logger = get_logger("engine.hybrid")


class AnalysisMode(Enum):
    """分析模式"""
    HYBRID = "hybrid"           # 混合模式
    RULES_ONLY = "rules_only"   # 仅规则引擎
    LLM_ONLY = "llm_only"       # 仅 LLM
    FALLBACK = "fallback"       # 降级模式


@dataclass
class HybridEngineConfig:
    """混合引擎配置"""
    # 模式选择
    mode: AnalysisMode = AnalysisMode.HYBRID
    
    # LLM 配置
    llm_enabled: bool = True
    llm_timeout: int = 30
    llm_max_retries: int = 3
    
    # 规则配置
    rules_enabled: bool = True
    min_confidence: float = 0.5
    
    # 降级配置
    fallback_on_llm_error: bool = True
    fallback_on_rules_error: bool = True
    
    # 聚合配置
    enable_deduplication: bool = True
    enable_cross_validation: bool = True


@dataclass
class AnalysisResult:
    """分析结果"""
    issues: List[Issue]
    mode: str
    execution_time: float
    issues_by_source: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    
    def summary(self) -> Dict[str, Any]:
        """生成摘要"""
        return {
            "total": len(self.issues),
            "high": sum(1 for i in self.issues if i.level == "high"),
            "medium": sum(1 for i in self.issues if i.level == "medium"),
            "low": sum(1 for i in self.issues if i.level == "low"),
            "by_source": self.issues_by_source,
        }


class HybridAnalysisEngine:
    """
    混合分析引擎
    
    整合多种分析能力：
    - 规则引擎：快速、准确的规则匹配
    - LLM：深度语义理解和上下文分析
    - 降级兜底：优雅处理失败情况
    """
    
    def __init__(self, config: Optional[HybridEngineConfig] = None):
        self.config = config or HybridEngineConfig()
        
        # 初始化组件
        self._init_components()
        
        logger.info(
            "hybrid_engine_initialized",
            mode=self.config.mode.value,
            llm_enabled=self.config.llm_enabled,
            rules_enabled=self.config.rules_enabled,
        )
    
    def _init_components(self):
        """初始化组件"""
        import time
        self._start_time = time.time()
        
        # 规则引擎
        self.rule_loader = RuleLoader()
        self.rule_manager = RuleManager()
        self.rules = self.rule_loader.load_all()
        
        # LLM 客户端（延迟初始化）
        self.llm_client = None
        self._llm_available = None
        
        # 降级引擎
        self.fallback_engine = FallbackEngine()
        self.fallback_engine.set_rules(self.rules)
        
        # 降级管理器
        self.degradation_manager = None  # 延迟初始化
    
    async def _get_llm_client(self):
        """获取 LLM 客户端（延迟初始化）"""
        if self.llm_client is None:
            from ..llm.client import LLMClient
            self.llm_client = LLMClient()
            
            # 初始化降级管理器
            self.degradation_manager = GracefulDegradation(
                llm_client=self.llm_client,
                rule_engine=self,
                fallback_engine=self.fallback_engine,
            )
        
        return self.llm_client
    
    async def _check_llm_available(self) -> bool:
        """检查 LLM 是否可用"""
        if self._llm_available is None:
            try:
                client = await self._get_llm_client()
                self._llm_available = await client.is_available()
            except Exception:
                self._llm_available = False
        
        return self._llm_available
    
    def analyze(self, document: Document, mode: Optional[str] = None) -> AnalysisResult:
        """
        同步分析文档
        
        Args:
            document: 文档对象
            mode: 分析模式，可选值: hybrid, rules_only, llm_only, fallback
            
        Returns:
            AnalysisResult: 分析结果
        """
        import time
        start_time = time.time()
        
        mode = mode or self.config.mode.value
        issues = []
        warnings = []
        issues_by_source = {}
        
        logger.info("analysis_started", mode=mode, file=document.metadata.file_name)
        
        try:
            if mode == AnalysisMode.RULES_ONLY.value or mode == "rules_only":
                issues, source_stats = self._analyze_rules_only(document)
                issues_by_source.update(source_stats)
                
            elif mode == AnalysisMode.LLM_ONLY.value or mode == "llm_only":
                issues, source_stats = asyncio.run(self._analyze_llm_only(document))
                issues_by_source.update(source_stats)
                
            elif mode == AnalysisMode.FALLBACK.value or mode == "fallback":
                issues = self._analyze_fallback(document)
                issues_by_source["fallback"] = len(issues)
                
            else:  # hybrid
                issues, source_stats = asyncio.run(self._analyze_hybrid(document))
                issues_by_source.update(source_stats)
        
        except Exception as e:
            logger.error("analysis_error", error=str(e))
            warnings.append(f"分析过程中出现错误: {e}")
            
            # 降级到启发式
            if self.config.fallback_on_llm_error:
                issues = self._analyze_fallback(document)
                issues_by_source["fallback"] = len(issues)
                warnings.append("已降级到启发式分析模式")
        
        # 去重
        if self.config.enable_deduplication:
            issues = self._deduplicate(issues)
        
        execution_time = time.time() - start_time
        
        logger.info(
            "analysis_completed",
            mode=mode,
            issues_found=len(issues),
            execution_time=f"{execution_time:.2f}s",
        )
        
        return AnalysisResult(
            issues=issues,
            mode=mode,
            execution_time=execution_time,
            issues_by_source=issues_by_source,
            warnings=warnings,
        )
    
    def _analyze_rules_only(self, document: Document) -> tuple[List[Issue], Dict[str, int]]:
        """纯规则分析"""
        issues = []
        source_stats = {"rule": 0}
        
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            matched_issues = self._match_rule(rule, document)
            issues.extend(matched_issues)
        
        source_stats["rule"] = len(issues)
        return issues, source_stats
    
    async def _analyze_llm_only(self, document: Document) -> tuple[List[Issue], Dict[str, int]]:
        """纯 LLM 分析"""
        issues = []
        source_stats = {"llm": 0}
        
        if await self._check_llm_available():
            try:
                client = await self._get_llm_client()
                issues = await client.analyze(document)
                source_stats["llm"] = len(issues)
            except Exception as e:
                logger.error("llm_analysis_failed", error=str(e))
                # 降级到启发式
                issues = self._analyze_fallback(document)
                source_stats["fallback"] = len(issues)
        else:
            logger.warning("llm_unavailable")
            issues = self._analyze_fallback(document)
            source_stats["fallback"] = len(issues)
        
        return issues, source_stats
    
    async def _analyze_hybrid(self, document: Document) -> tuple[List[Issue], Dict[str, int]]:
        """混合分析"""
        issues = []
        source_stats = {}
        
        # 1. 规则引擎快速扫描
        if self.config.rules_enabled:
            rule_issues, rule_stats = self._analyze_rules_only(document)
            issues.extend(rule_issues)
            source_stats.update(rule_stats)
        
        # 2. LLM 深度分析
        if self.config.llm_enabled:
            try:
                if await self._check_llm_available():
                    llm_issues, llm_stats = await self._analyze_llm_only(document)
                    
                    # 3. 交叉验证
                    if self.config.enable_cross_validation and rule_issues:
                        validated = self._cross_validate(rule_issues, llm_issues)
                        # 合并，去除重复
                        existing_ids = {i.id for i in issues}
                        for issue in validated:
                            if issue.id not in existing_ids:
                                issues.append(issue)
                    else:
                        issues.extend(llm_issues)
                    
                    source_stats.update(llm_stats)
                else:
                    logger.warning("llm_unavailable_in_hybrid")
                    source_stats["llm"] = 0
                    
            except Exception as e:
                logger.error("llm_analysis_failed_in_hybrid", error=str(e))
                source_stats["llm_error"] = str(e)
        
        return issues, source_stats
    
    def _analyze_fallback(self, document: Document) -> List[Issue]:
        """降级分析（启发式）"""
        return self.fallback_engine.analyze(document)
    
    def _match_rule(self, rule: Dict, document: Document) -> List[Issue]:
        """匹配规则"""
        import re
        
        issues = []
        
        # 获取触发条件
        trigger = rule.get("trigger", {})
        keywords = trigger.get("match", [])
        
        if not keywords:
            return issues
        
        # 获取文档文本
        text = document.full_text if hasattr(document, 'full_text') else str(document)
        
        # 关键词匹配
        for keyword in keywords:
            pattern = re.escape(keyword)
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                # 获取上下文
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # 提取引用
                quote = text[match.start():match.end() + 100]
                
                issue = Issue(
                    id=f"{rule['id']}_{match.start()}",
                    type="rule_match",
                    category=rule.get("category", "other"),
                    level=rule.get("level", "medium"),
                    title=rule.get("name", "发现问题"),
                    evidence=None,  # 稍后填充
                    rule=None,
                    suggestion=None,
                    confidence=0.8,
                    source="rule",
                )
                
                # 填充证据
                from models.issue import IssueEvidence, IssueLocation, IssueSuggestion, IssueRule
                
                location = IssueLocation(line_start=0, line_end=0)
                issue.evidence = IssueEvidence(
                    quote=quote,
                    location=location,
                    highlight=keyword,
                )
                
                # 填充法规依据
                ref = rule.get("reference", [])
                ref_text = ref[0] if ref else ""
                issue.rule = IssueRule(
                    id=rule.get("id", ""),
                    name=rule.get("name", ""),
                    reference=ref_text,
                )
                
                # 填充建议
                suggestion_template = rule.get("suggestion", {}).get("template", "")
                issue.suggestion = IssueSuggestion(content=suggestion_template)
                
                issues.append(issue)
        
        return issues
    
    def _cross_validate(
        self, 
        rule_issues: List[Issue], 
        llm_issues: List[Issue]
    ) -> List[Issue]:
        """交叉验证 LLM 结果"""
        validated = []
        
        for llm_issue in llm_issues:
            confirmed = False
            
            # 检查是否有规则也发现了同样的问题
            for rule_issue in rule_issues:
                if self._is_similar(llm_issue, rule_issue):
                    confirmed = True
                    # 规则确认，提升置信度
                    llm_issue.confidence = min(1.0, llm_issue.confidence + 0.2)
                    llm_issue.source = "llm+rule"
                    break
            
            # 如果未被规则确认，降低置信度
            if not confirmed and llm_issue.confidence > 0.5:
                llm_issue.confidence = llm_issue.confidence * 0.8
            
            validated.append(llm_issue)
        
        return validated
    
    def _is_similar(self, issue1: Issue, issue2: Issue) -> bool:
        """判断两个问题是否相似"""
        # 同类别
        if issue1.category != issue2.category:
            return False
        
        # 检查关键词重叠
        if issue1.evidence and issue2.evidence:
            text1 = issue1.evidence.highlight or ""
            text2 = issue2.evidence.highlight or ""
            
            # 简单关键词匹配
            if text1 and text2:
                return text1.lower() in text2.lower() or text2.lower() in text1.lower()
        
        return False
    
    def _deduplicate(self, issues: List[Issue]) -> List[Issue]:
        """去重"""
        seen = set()
        unique = []
        
        for issue in issues:
            # 生成唯一键
            key = self._issue_key(issue)
            
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        
        return unique
    
    def _issue_key(self, issue: Issue) -> str:
        """生成问题唯一键"""
        category = issue.category or "other"
        level = issue.level or "low"
        title = issue.title or ""
        
        # 基于标题和级别去重
        return f"{category}_{level}_{title[:50]}"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "rules_loaded": len(self.rules),
            "config": {
                "mode": self.config.mode.value,
                "llm_enabled": self.config.llm_enabled,
                "rules_enabled": self.config.rules_enabled,
            },
            "fallback_stats": self.fallback_engine.get_stats() if self.fallback_engine else {},
        }


# 导出
__all__ = [
    'HybridAnalysisEngine',
    'HybridEngineConfig',
    'AnalysisMode',
    'AnalysisResult',
]
