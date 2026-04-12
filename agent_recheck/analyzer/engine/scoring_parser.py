# -*- coding: utf-8 -*-
"""
评分标准解析器

负责解析政府采购文件中的评分标准相关表格：
- 评分因素提取
- 分值权重计算
- 客观分/主观分识别
- 价格分公式解析
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ScoreType(Enum):
    """分值类型"""
    PRICE = "price"           # 价格分
    TECHNICAL = "technical"   # 技术分
    COMMERCIAL = "commercial" # 商务分
    COMPREHENSIVE = "comprehensive"  # 综合分
    UNKNOWN = "unknown"


class EvaluationMethod(Enum):
    """评审方法"""
    LOWEST_PRICE = "lowest_price"           # 最低价法
    COMPREHENSIVE = "comprehensive"          # 综合评分法
    QUALIFICATION = "qualification"         # 资格后审
    UNKNOWN = "unknown"


@dataclass
class ScoringItem:
    """评分项"""
    name: str                          # 评分项名称
    score: int                         # 分值
    score_type: ScoreType              # 分值类型
    is_objective: bool                 # 是否为客观分
    description: str = ""              # 描述
    calculation_method: Optional[str] = None  # 计算方法
    is_substantiative: bool = False   # 是否为实质性条款
    keywords: List[str] = field(default_factory=list)  # 触发关键词


@dataclass
class ScoringStandard:
    """评分标准"""
    evaluation_method: EvaluationMethod  # 评审方法
    total_score: int                    # 总分
    items: List[ScoringItem] = field(default_factory=list)  # 评分项
    price_formula: Optional[str] = None # 价格分计算公式
    price_weight: float = 0.0          # 价格分权重
    technical_weight: float = 0.0       # 技术分权重
    commercial_weight: float = 0.0      # 商务分权重
    
    @property
    def objective_score(self) -> int:
        """客观分总分"""
        return sum(item.score for item in self.items if item.is_objective)
    
    @property
    def subjective_score(self) -> int:
        """主观分总分"""
        return sum(item.score for item in self.items if not item.is_objective)


@dataclass
class PriceFormula:
    """价格分公式"""
    formula_type: str                  # 公式类型
    formula_text: str                   # 公式文本
    max_score: int                     # 最高分
    min_score: int                     # 最低分
    benchmark: Optional[float] = None  # 基准价


class ScoringParser:
    """
    评分标准解析器
    
    功能：
    - 提取评分因素和分值
    - 解析价格分计算公式
    - 区分客观分和主观分
    - 验证评分标准合规性
    """
    
    # 评分因素关键词
    SCORING_FACTORS = {
        'price': ['价格', '报价', '投标价', '总价', '单价'],
        'technical': ['技术', '功能', '性能', '方案', '设计'],
        'commercial': ['商务', '业绩', '资质', '服务', '履约'],
    }
    
    # 客观分判定关键词
    OBJECTIVE_KEYWORDS = [
        '证书', '认证', '资质', '业绩', 'ISO', '营业执照',
        '检测报告', '参数', '规格', '型号', '数量'
    ]
    
    # 主观分判定关键词
    SUBJECTIVE_KEYWORDS = [
        '方案', '设计', '创意', '思路', '理解', '可行性',
        '综合', '整体', '水平', '能力'
    ]
    
    # 价格分公式模式
    PRICE_FORMULA_PATTERNS = [
        # 最低价法
        (r'(?:最低价|最低报价)', 'lowest_price'),
        # 公式法
        (r'价格分\s*=\s*\d+.*?(?:最高|满分)', 'formula_based'),
        # 线性公式
        (r'(?:基准价|评标基准价).*?[\d\.]+', 'linear'),
        # 低价优先
        (r'价格分\s*=.*?(?:最低|优)', 'lowest_priority'),
    ]
    
    def __init__(self):
        self.standards: List[ScoringStandard] = []
    
    def parse_scoring_table(self, table_text: str) -> Optional[ScoringStandard]:
        """
        解析评分标准表格
        
        Args:
            table_text: 表格文本内容
            
        Returns:
            ScoringStandard: 评分标准对象
        """
        standard = ScoringStandard(
            evaluation_method=self._detect_evaluation_method(table_text),
            total_score=0
        )
        
        # 解析评审方法
        method = standard.evaluation_method
        
        # 提取价格分权重
        price_weight = self._extract_price_weight(table_text)
        standard.price_weight = price_weight
        
        # 提取评分项
        items = self._extract_scoring_items(table_text)
        standard.items = items
        standard.total_score = sum(item.score for item in items)
        
        # 解析价格公式
        price_formula = self._parse_price_formula(table_text)
        if price_formula:
            standard.price_formula = price_formula.formula_text
        
        # 计算权重分配
        self._calculate_weights(standard)
        
        return standard
    
    def _detect_evaluation_method(self, text: str) -> EvaluationMethod:
        """检测评审方法"""
        text_lower = text.lower()
        
        if '最低价' in text:
            return EvaluationMethod.LOWEST_PRICE
        elif '综合评分' in text or '综合得分' in text:
            return EvaluationMethod.COMPREHENSIVE
        elif '资格' in text and '后审' in text:
            return EvaluationMethod.QUALIFICATION
        
        return EvaluationMethod.UNKNOWN
    
    def _extract_price_weight(self, text: str) -> float:
        """提取价格分权重"""
        patterns = [
            r'价格分[权重分]?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%',
            r'价格\s*[权重分]?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%.*?价格',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        
        return 0.0
    
    def _extract_scoring_items(self, text: str) -> List[ScoringItem]:
        """提取评分项"""
        items = []
        
        # 常见的评分项模式
        # 格式: 评分因素 \t 分值 或 评分因素 ... 分值
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 提取分值
            score = self._extract_score_from_line(line)
            if score is None or score == 0:
                continue
            
            # 确定评分项类型
            score_type = self._classify_item_type(line)
            
            # 判断是否为客观分
            is_objective = self._is_objective_item(line)
            
            # 判断是否为实质性条款
            is_substantiative = '★' in line or '实质性' in line
            
            # 提取评分项名称
            name = self._extract_item_name(line)
            
            if name:
                items.append(ScoringItem(
                    name=name,
                    score=score,
                    score_type=score_type,
                    is_objective=is_objective,
                    is_substantiative=is_substantiative,
                    description=line[:200],
                    keywords=self._extract_keywords(line)
                ))
        
        return items
    
    def _extract_score_from_line(self, line: str) -> Optional[int]:
        """从行中提取分值"""
        patterns = [
            r'(\d+)\s*分',           # XX分
            r'分值?\s*[:：]?\s*(\d+)',  # 分值:XX
            r'\[(\d+)\]',            # [XX]
            r'（(\d+)）',            # （XX）
            r'(\d+)\s*/\s*\d+',      # XX/XX
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_item_name(self, line: str) -> Optional[str]:
        """提取评分项名称"""
        # 移除分值部分
        name = re.sub(r'\d+\s*分', '', line)
        name = re.sub(r'\[.*?\]', '', name)
        name = re.sub(r'（.*?）', '', name)
        name = re.sub(r'[★▲◆■]', '', name)
        
        # 清理
        name = name.strip('：:、,，.。 ')
        
        if len(name) >= 2 and len(name) <= 50:
            return name
        
        return None
    
    def _classify_item_type(self, line: str) -> ScoreType:
        """分类评分项类型"""
        for score_type, keywords in self.SCORING_FACTORS.items():
            for keyword in keywords:
                if keyword in line:
                    return ScoreType(score_type)
        
        return ScoreType.UNKNOWN
    
    def _is_objective_item(self, line: str) -> bool:
        """判断是否为客观分"""
        # 检查客观分关键词
        for keyword in self.OBJECTIVE_KEYWORDS:
            if keyword in line:
                return True
        
        # 检查主观分关键词
        for keyword in self.SUBJECTIVE_KEYWORDS:
            if keyword in line:
                return False
        
        # 默认按客观分处理（政府采购中客观分占多数）
        return True
    
    def _extract_keywords(self, line: str) -> List[str]:
        """提取关键词"""
        keywords = []
        all_keywords = sum(self.SCORING_FACTORS.values(), [])
        
        for keyword in all_keywords:
            if keyword in line:
                keywords.append(keyword)
        
        return keywords
    
    def _parse_price_formula(self, text: str) -> Optional[PriceFormula]:
        """解析价格分计算公式"""
        # 匹配价格公式
        formula_patterns = [
            # 线性插值法
            (r'价格分\s*=\s*\d+\s*×\s*\(\s*\d+\s*-\s*(?:投标报价|报价)\s*\)\s*/\s*\d+',
             'linear_interpolation'),
            # 最低价法
            (r'最低报价\s*[×*]\s*\d+\s*/\s*(?:投标报价|报价)', 'lowest_price'),
            # 基准价法
            (r'基准价.*?价格分', 'benchmark'),
        ]
        
        for pattern, formula_type in formula_patterns:
            match = re.search(pattern, text)
            if match:
                return PriceFormula(
                    formula_type=formula_type,
                    formula_text=match.group(0),
                    max_score=100,
                    min_score=0
                )
        
        # 如果没有明确公式，检查是否为低价优先
        if '低价优先' in text or '最低价' in text:
            return PriceFormula(
                formula_type='lowest_price',
                formula_text='价格分 = 最低报价 × 满分 / 投标报价',
                max_score=100,
                min_score=0
            )
        
        return None
    
    def _calculate_weights(self, standard: ScoringStandard):
        """计算权重分配"""
        if standard.total_score == 0:
            return
        
        price_score = sum(
            item.score for item in standard.items 
            if item.score_type == ScoreType.PRICE
        )
        technical_score = sum(
            item.score for item in standard.items 
            if item.score_type == ScoreType.TECHNICAL
        )
        commercial_score = sum(
            item.score for item in standard.items 
            if item.score_type == ScoreType.COMMERCIAL
        )
        
        standard.price_weight = price_score / standard.total_score * 100
        standard.technical_weight = technical_score / standard.total_score * 100
        standard.commercial_weight = commercial_score / standard.total_score * 100
    
    def validate_scoring_standard(self, standard: ScoringStandard) -> List[Dict]:
        """
        验证评分标准合规性
        
        Returns:
            问题列表
        """
        issues = []
        
        # 检查总分
        if standard.total_score != 100:
            issues.append({
                'type': 'total_score',
                'severity': 'warning',
                'message': f'评分总分 {standard.total_score} 不等于 100'
            })
        
        # 检查价格分权重
        if standard.evaluation_method == EvaluationMethod.COMPREHENSIVE:
            if standard.price_weight > 70:
                issues.append({
                    'type': 'price_weight',
                    'severity': 'warning',
                    'message': f'价格分权重 {standard.price_weight}% 超过 70%，可能存在风险'
                })
            elif standard.price_weight < 10:
                issues.append({
                    'type': 'price_weight',
                    'severity': 'info',
                    'message': f'价格分权重 {standard.price_weight}% 较低，可能影响竞争性'
                })
        
        # 检查主观分比例
        subjective_ratio = standard.subjective_score / standard.total_score if standard.total_score > 0 else 0
        if subjective_ratio > 0.5:
            issues.append({
                'type': 'subjective_ratio',
                'severity': 'warning',
                'message': f'主观分占比 {subjective_ratio:.1%} 超过 50%，存在评审风险'
            })
        
        # 检查实质性条款
        substantiative_items = [item for item in standard.items if item.is_substantiative]
        if not substantiative_items:
            issues.append({
                'type': 'substantiative',
                'severity': 'info',
                'message': '未发现明确的实质性评分条款'
            })
        
        return issues
    
    def summarize(self, standard: ScoringStandard) -> Dict[str, Any]:
        """生成评分标准摘要"""
        return {
            'evaluation_method': standard.evaluation_method.value,
            'total_score': standard.total_score,
            'price_weight': f"{standard.price_weight:.1f}%",
            'technical_weight': f"{standard.technical_weight:.1f}%",
            'commercial_weight': f"{standard.commercial_weight:.1f}%",
            'objective_score': standard.objective_score,
            'subjective_score': standard.subjective_score,
            'item_count': len(standard.items),
            'substantiative_count': sum(1 for item in standard.items if item.is_substantiative),
            'has_price_formula': standard.price_formula is not None,
        }
