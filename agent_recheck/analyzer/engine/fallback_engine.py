# -*- coding: utf-8 -*-
"""
降级兜底引擎

当 LLM 服务不可用或响应失败时，提供规则引擎的兜底分析：
- 纯规则模式
- 混合模式（规则 + 启发式）
- 最小化模式（仅关键规则）
"""

import re
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from models.issue import Issue, IssueLevel
from utils.logging import get_logger

logger = get_logger("fallback_engine")


class FallbackMode(Enum):
    """降级模式"""
    FULL_RULES = "full_rules"       # 完整规则模式
    HYBRID = "hybrid"               # 混合模式（规则 + 启发式）
    MINIMAL = "minimal"             # 最小化模式（仅关键规则）


@dataclass
class FallbackConfig:
    """降级配置"""
    mode: FallbackMode = FallbackMode.FULL_RULES
    
    # 规则覆盖
    use_discrimination_rules: bool = True
    use_scoring_rules: bool = True
    use_qualification_rules: bool = True
    use_contract_rules: bool = True
    
    # 启发式规则
    use_heuristics: bool = True
    
    # 阈值
    min_confidence: float = 0.5
    

class FallbackEngine:
    """
    降级兜底引擎
    
    当 LLM 不可用时，使用规则引擎和启发式方法进行分析
    """
    
    # 启发式规则：常见的违规模式
    HEURISTIC_PATTERNS = {
        # 非歧视性
        "地域限定": {
            "patterns": [
                r"本省[以内]?业绩",
                r"本市[内]?业绩",
                r"深圳市业绩",
                r"本区业绩",
                r"必须在本.*设有",
            ],
            "level": "high",
            "category": "discrimination",
            "suggestion": "业绩要求不应限定特定地域",
        },
        "品牌指向": {
            "patterns": [
                r"必须是.*品牌",
                r"等同于.*品牌",
                r"参照.*品牌",
                r"指定品牌",
            ],
            "level": "high",
            "category": "discrimination",
            "suggestion": "技术参数不应指定特定品牌",
        },
        # 评分标准
        "价格分过高": {
            "patterns": [
                r"价格分\s*[≥>]\s*7\s*0\s*%",
                r"价格分.*?80%",
                r"价格分.*?90%",
            ],
            "level": "medium",
            "category": "scoring",
            "suggestion": "价格分权重不宜过高",
        },
        "主观分过高": {
            "patterns": [
                r"技术分.*?6\s*0\s*%",
                r"方案分.*?5\s*0\s*%",
            ],
            "level": "medium",
            "category": "scoring",
            "suggestion": "主观分权重不宜过高",
        },
        # 资质要求
        "过高资质": {
            "patterns": [
                r"正高级.*?工程师",
                r"一级建造师.*?[中小]?项目",
            ],
            "level": "medium",
            "category": "qualification",
            "suggestion": "资质要求应与项目规模相匹配",
        },
        # 合同条款
        "保证金过高": {
            "patterns": [
                r"履约保证金.*?2\s*0\s*%",
                r"保证金.*?合同价格.*?2\s*0\s*%",
            ],
            "level": "medium",
            "category": "contract",
            "suggestion": "履约保证金不宜超过合同金额的10%",
        },
        # 认证证书
        "认证指向": {
            "patterns": [
                r"SA8000.*?认证",
                r"必须.*?认证",
            ],
            "level": "high",
            "category": "certification",
            "suggestion": "认证要求应有合理依据",
        },
    }
    
    # 关键标记
    CRITICAL_MARKERS = {
        "★": {"level": "high", "name": "实质性条款"},
        "■": {"level": "high", "name": "重要条款"},
        "▲": {"level": "medium", "name": "注意事项"},
    }
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self._rules_cache = {}
    
    def analyze(self, document) -> List[Issue]:
        """
        使用降级模式分析文档
        
        Args:
            document: 文档对象（ParsedDocument）
            
        Returns:
            发现的问题列表
        """
        issues = []
        
        # 1. 启发式分析
        if self.config.use_heuristics:
            issues.extend(self._heuristic_analysis(document))
        
        # 2. 标记分析
        issues.extend(self._marker_analysis(document))
        
        # 3. 关键内容分析
        issues.extend(self._critical_content_analysis(document))
        
        return issues
    
    def _heuristic_analysis(self, document) -> List[Issue]:
        """启发式规则分析"""
        issues = []
        full_text = document.full_text if hasattr(document, 'full_text') else str(document)
        
        for rule_name, rule_config in self.HEURISTIC_PATTERNS.items():
            patterns = rule_config.get("patterns", [])
            
            for pattern in patterns:
                matches = re.finditer(pattern, full_text, re.IGNORECASE)
                
                for match in matches:
                    # 获取上下文
                    start = max(0, match.start() - 50)
                    end = min(len(full_text), match.end() + 50)
                    context = full_text[start:end]
                    
                    issue = Issue(
                        id=f"heuristic_{rule_name}_{match.start()}",
                        type="heuristic",
                        category=rule_config.get("category", "other"),
                        level=rule_config.get("level", "medium"),
                        title=f"疑似违规: {rule_name}",
                        evidence=None,  # 稍后填充
                        rule=None,
                        suggestion=rule_config.get("suggestion", ""),
                        confidence=0.7,
                        source="fallback_heuristic",
                    )
                    
                    issues.append(issue)
        
        return issues
    
    def _marker_analysis(self, document) -> List[Issue]:
        """关键标记分析"""
        issues = []
        full_text = document.full_text if hasattr(document, 'full_text') else str(document)
        
        for marker, marker_config in self.CRITICAL_MARKERS.items():
            # 查找所有标记位置
            pattern = rf"{re.escape(marker)}[^\n]{{0,100}}"
            matches = re.finditer(pattern, full_text)
            
            for match in matches:
                text = match.group()
                
                # 检查是否缺少实质性要求
                if self._is_missing_substantiative(text):
                    issue = Issue(
                        id=f"marker_{marker}_{match.start()}",
                        type="marker",
                        category="procurement",
                        level=marker_config.get("level", "medium"),
                        title=f"{marker_config.get('name')} 缺少核心内容",
                        evidence=None,
                        rule=None,
                        suggestion="请补充完整的实质性条款内容",
                        confidence=0.6,
                        source="fallback_marker",
                    )
                    issues.append(issue)
        
        return issues
    
    def _critical_content_analysis(self, document) -> List[Issue]:
        """关键内容完整性分析"""
        issues = []
        full_text = document.full_text if hasattr(document, 'full_text') else str(document)
        
        # 检查关键条款是否完整
        required_items = {
            "交货期": r"交货期|交付时间|供货期",
            "付款方式": r"付款|支付|结算",
            "质保期": r"质保期|质量保证期|保修期",
            "履约保证金": r"履约保证金|保证金比例",
        }
        
        for item_name, pattern in required_items.items():
            if not re.search(pattern, full_text, re.IGNORECASE):
                issue = Issue(
                    id=f"missing_{item_name}",
                    type="completeness",
                    category="contract",
                    level="medium",
                    title=f"缺少{item_name}条款",
                    evidence=None,
                    rule=None,
                    suggestion=f"建议补充完整的{item_name}条款",
                    confidence=0.5,
                    source="fallback_completeness",
                )
                issues.append(issue)
        
        return issues
    
    def _is_missing_substantiative(self, text: str) -> bool:
        """检查是否缺少实质性内容"""
        # 简单检查：文本过短或包含省略号
        if len(text) < 20:
            return True
        if "…" in text or "..." in text:
            return True
        return False
    
    def set_rules(self, rules: List[Dict]):
        """设置规则数据"""
        self._rules_cache = {r.get("id"): r for r in rules}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "mode": self.config.mode.value,
            "rules_loaded": len(self._rules_cache),
            "heuristics_enabled": self.config.use_heuristics,
        }


class GracefulDegradation:
    """
    优雅降级管理器
    
    管理 LLM 和规则引擎之间的切换
    """
    
    def __init__(
        self,
        llm_client: Any,
        rule_engine: Any,
        fallback_engine: FallbackEngine,
    ):
        self.llm_client = llm_client
        self.rule_engine = rule_engine
        self.fallback_engine = fallback_engine
        self._failure_count = 0
        self._failure_threshold = 3
    
    async def analyze(self, document) -> tuple[List[Issue], str]:
        """
        智能分析文档
        
        优先使用 LLM，失败时降级到规则引擎，再失败时使用启发式
        
        Returns:
            (问题列表, 分析模式)
        """
        # 模式1: 尝试 LLM
        if await self._is_llm_available():
            try:
                issues = await self.llm_client.analyze(document)
                self._failure_count = 0  # 重置失败计数
                return issues, "llm"
            except Exception as e:
                logger.warning("llm_analysis_failed_using_fallback", error=str(e))
                self._failure_count += 1
        
        # 模式2: 规则引擎
        if self.rule_engine:
            try:
                issues = self.rule_engine.analyze(document)
                if self._failure_count >= self._failure_threshold:
                    return issues, "rules"
            except Exception as e:
                logger.warning("rule_analysis_failed_using_fallback", error=str(e))
        
        # 模式3: 降级兜底
        issues = self.fallback_engine.analyze(document)
        return issues, "fallback"
    
    async def _is_llm_available(self) -> bool:
        """检查 LLM 是否可用"""
        try:
            return await self.llm_client.is_available()
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "degraded": self._failure_count >= self._failure_threshold,
        }


# 导出
__all__ = [
    'FallbackEngine',
    'FallbackMode',
    'FallbackConfig',
    'GracefulDegradation',
]
