# -*- coding: utf-8 -*-
"""
本地化规则引擎

支持地方性法规和行业特殊要求：
- 深圳经济特区政府采购条例
- 广东省政府采购条例
- 各省市特殊规定
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import yaml
import os


@dataclass
class LocalRule:
    """本地化规则"""
    id: str
    name: str
    region: str  # 适用地区
    industry: Optional[str] = None  # 适用行业
    priority: int = 0  # 优先级，数字越大优先级越高
    description: str = ""
    keywords: List[str] = None  # 触发关键词
    exclusion_keywords: List[str] = None  # 排除关键词
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.exclusion_keywords is None:
            self.exclusion_keywords = []


class LocalRuleEngine:
    """
    本地化规则引擎
    
    提供基于地区和行业的规则过滤和匹配
    """
    
    # 地区规则映射
    REGION_RULES = {
        "深圳": "深圳经济特区政府采购条例",
        "广东": "广东省政府采购条例",
        "广州": "广东省政府采购条例",
        "珠海": "广东省政府采购条例",
        "东莞": "广东省政府采购条例",
        "浙江": "浙江省政府采购管理办法",
        "杭州": "浙江省政府采购管理办法",
        "宁波": "浙江省政府采购管理办法",
    }
    
    # 地区特有违规关键词
    REGION_SPECIFIC_VIOLATIONS = {
        "深圳": [
            # 深圳特有的条例要求
            "深圳政府采购",
            "特区采购",
        ],
        "广东": [
            # 广东省条例要求
            "省产",
            "粤产",
        ],
    }
    
    def __init__(self, rules_dir: Optional[str] = None):
        self.rules_dir = rules_dir
        self.local_rules: Dict[str, List[LocalRule]] = {}
        self._load_rules()
    
    def _load_rules(self):
        """加载本地化规则"""
        if not self.rules_dir:
            return
        
        # 加载各地区规则
        for region in self.REGION_RULES.keys():
            region_dir = os.path.join(self.rules_dir, region.lower())
            if os.path.exists(region_dir):
                self._load_region_rules(region, region_dir)
    
    def _load_region_rules(self, region: str, region_dir: str):
        """加载指定地区的规则"""
        self.local_rules[region] = []
        
        for filename in os.listdir(region_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(region_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        rule = LocalRule(
                            id=data.get('id', filename),
                            name=data.get('name', ''),
                            region=region,
                            industry=data.get('industry'),
                            priority=data.get('priority', 0),
                            description=data.get('description', ''),
                            keywords=data.get('keywords', []),
                            exclusion_keywords=data.get('exclusion_keywords', [])
                        )
                        self.local_rules[region].append(rule)
    
    def get_applicable_rules(
        self, 
        region: Optional[str] = None, 
        industry: Optional[str] = None
    ) -> List[LocalRule]:
        """
        获取适用的本地化规则
        
        Args:
            region: 地区名称（如 "深圳"）
            industry: 行业名称（如 "医疗设备"）
            
        Returns:
            适用的规则列表，按优先级排序
        """
        if not region:
            return []
        
        rules = self.local_rules.get(region, [])
        
        # 按行业过滤
        if industry:
            industry_rules = [r for r in rules if r.industry is None or r.industry == industry]
        else:
            industry_rules = rules
        
        # 按优先级排序
        return sorted(industry_rules, key=lambda r: r.priority, reverse=True)
    
    def check_violation(
        self, 
        text: str, 
        region: Optional[str] = None,
        industry: Optional[str] = None
    ) -> List[Dict]:
        """
        检查文本是否违反本地化规则
        
        Returns:
            违规列表 [{'rule': LocalRule, 'match': str}]
        """
        violations = []
        
        applicable_rules = self.get_applicable_rules(region, industry)
        
        for rule in applicable_rules:
            # 检查关键词匹配
            for keyword in rule.keywords:
                if keyword in text:
                    # 检查是否被排除
                    excluded = any(ex_kw in text for ex_kw in rule.exclusion_keywords)
                    if not excluded:
                        violations.append({
                            'rule': rule,
                            'keyword': keyword,
                            'text': text[:200]
                        })
        
        return violations
    
    def get_region_law_name(self, region: str) -> Optional[str]:
        """获取地区对应的法规名称"""
        return self.REGION_RULES.get(region)
    
    def is_valid_region(self, region: str) -> bool:
        """检查是否为已知地区"""
        return region in self.REGION_RULES


class RegionDetector:
    """地区检测器 - 根据文档内容推断地区"""
    
    REGION_PATTERNS = {
        "深圳": [
            r'深圳经济特区',
            r'深圳市',
            r'SZCG\d',
            r'SZ\d{8}',
        ],
        "广东": [
            r'广东省',
            r'GD\d{8}',
            r'GPC\d',
        ],
        "广州": [
            r'广州市',
            r'GZCG\d',
        ],
        "浙江": [
            r'浙江省',
            r'ZJCG\d',
            r'浙江政采',
        ],
        "北京": [
            r'北京市',
            r'BG\d{6}',
        ],
        "上海": [
            r'上海市',
            r'SHGP\d',
        ],
    }
    
    def detect(self, text: str) -> Optional[str]:
        """
        检测文档所属地区
        
        Returns:
            地区名称，如果无法确定返回 None
        """
        import re
        
        scores = {}
        for region, patterns in self.REGION_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text):
                    score += 1
            if score > 0:
                scores[region] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return None
    
    def get_all_detected_regions(self, text: str) -> List[str]:
        """获取所有检测到的地区"""
        detected = []
        import re
        
        for region, patterns in self.REGION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    if region not in detected:
                        detected.append(region)
                    break
        
        return detected
