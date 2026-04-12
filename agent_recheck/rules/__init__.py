# -*- coding: utf-8 -*-
"""
规则配置模块

包含所有合规性审查规则，按类别组织：
- discrimination: 非歧视性规则
- scoring: 评分标准规则
- contract: 合同条款规则
- certifications: 认证证书规则
- qualification: 资质要求规则
- procurement: 采购需求规则
- shenzhen: 深圳特有规则
"""

import os
from pathlib import Path

# 规则目录
RULES_DIR = Path(__file__).parent

# 规则类别映射
RULE_CATEGORIES = {
    'discrimination': '非歧视性规则',
    'scoring': '评分标准规则',
    'contract': '合同条款规则',
    'certifications': '认证证书规则',
    'qualification': '资质要求规则',
    'procurement': '采购需求规则',
    'shenzhen': '深圳特有规则',
}


def get_rules_by_category(category: str) -> list:
    """获取指定类别的所有规则"""
    category_dir = RULES_DIR / category
    if not category_dir.exists():
        return []
    
    rules = []
    for file in category_dir.glob('*.yaml'):
        rules.append(str(file))
    
    return rules


def get_all_rules() -> dict:
    """获取所有规则，按类别组织"""
    all_rules = {}
    
    for category in RULE_CATEGORIES.keys():
        rules = get_rules_by_category(category)
        if rules:
            all_rules[category] = rules
    
    return all_rules


def list_categories() -> dict:
    """列出所有规则类别"""
    return RULE_CATEGORIES.copy()


__all__ = [
    'RULES_DIR',
    'RULE_CATEGORIES',
    'get_rules_by_category',
    'get_all_rules',
    'list_categories',
]
