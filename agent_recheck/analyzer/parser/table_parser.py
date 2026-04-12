# -*- coding: utf-8 -*-
"""
表格解析器模块

负责解析政府采购文档中的各类表格，包括：
- 嵌套表格识别
- 表格标题自动关联
- 跨表格数据一致性检查
- 特殊标记识别（★, ▲等）
"""

from .enhanced_table_parser import EnhancedTableParser, TableMetadata, TableCell

__all__ = ['EnhancedTableParser', 'TableMetadata', 'TableCell']
