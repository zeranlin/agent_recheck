# -*- coding: utf-8 -*-
"""
增强型表格解析器

基于深圳政府采购文档样本分析：
- 每个文档平均 15-25 个表格
- 包含评分标准表、技术参数表、资质要求表等
- 使用 ★ 标记实质性条款，▲ 标记重要参数
- 表格可能包含嵌套结构
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Set
from enum import Enum


class CellType(Enum):
    """单元格类型"""
    NORMAL = "normal"
    HEADER = "header"
    MERGED = "merged"
    HIGHLIGHTED_STAR = "highlighted_star"  # ★ 标记
    HIGHLIGHTED_TRIANGLE = "highlighted_triangle"  # ▲ 标记
    CRITICAL = "critical"  # 实质性条款


class TableType(Enum):
    """表格类型"""
    UNKNOWN = "unknown"
    SCORING_STANDARD = "scoring_standard"  # 评分标准表
    TECHNICAL_REQUIREMENT = "technical_requirement"  # 技术需求表
    QUALIFICATION = "qualification"  # 资质要求表
    CONTRACT_TERM = "contract_term"  # 合同条款表
    SUBSTANTIATIVE = "substantiative"  # 实质性条款表


@dataclass
class TableCell:
    """表格单元格"""
    text: str
    row: int
    col: int
    cell_type: CellType = CellType.NORMAL
    is_header: bool = False
    is_merged: bool = False
    is_substantiative: bool = False  # 是否为实质性条款
    raw_xml: Optional[str] = None
    
    def clean_text(self) -> str:
        """清理单元格文本"""
        text = self.text.strip()
        # 移除特殊标记但保留文本
        text = re.sub(r'[★▲◆■]', '', text)
        return text.strip()
    
    def has_critical_marker(self) -> bool:
        """检查是否包含关键标记"""
        return '★' in self.text or '▲' in self.text


@dataclass
class TableRow:
    """表格行"""
    cells: List[TableCell]
    row_index: int
    is_header_row: bool = False


@dataclass
class TableMetadata:
    """表格元信息"""
    table_id: int
    table_type: TableType = TableType.UNKNOWN
    
    # 标题和位置
    title: Optional[str] = None
    preceding_paragraph: Optional[str] = None
    following_paragraph: Optional[str] = None
    
    # 结构信息
    row_count: int = 0
    col_count: int = 0
    
    # 关键内容
    has_substantiative: bool = False  # 是否包含实质性条款
    substantiative_count: int = 0
    critical_keywords: List[str] = field(default_factory=list)
    
    # 关联信息
    linked_section: Optional[str] = None  # 关联的章节
    cross_references: List[str] = field(default_factory=list)  # 交叉引用
    
    # 原始数据
    raw_element: Optional[Any] = None


class EnhancedTableParser:
    """
    增强型表格解析器
    
    特性：
    - 识别嵌套表格
    - 提取表格标题和注释
    - 处理合并单元格
    - 关联表格与上下文段落
    - 识别关键标记（★, ▲）
    - 自动判断表格类型
    """
    
    # 表格类型识别关键词
    TABLE_TYPE_KEYWORDS = {
        TableType.SCORING_STANDARD: [
            '评分', '价格分', '技术分', '商务分', '综合评分',
            '评审因素', '分值', '权重', '得分'
        ],
        TableType.TECHNICAL_REQUIREMENT: [
            '技术参数', '规格', '要求', '配置', '性能指标',
            '功能要求', '技术需求'
        ],
        TableType.QUALIFICATION: [
            '资质', '认证', '证书', '业绩', '人员要求',
            '资格', '营业执照', 'ISO'
        ],
        TableType.CONTRACT_TERM: [
            '合同', '付款', '交货', '质保', '验收',
            '违约', '索赔', '争议解决'
        ],
        TableType.SUBSTANTIATIVE: [
            '实质性', '必须', '不得', '严禁', '★'
        ]
    }
    
    # 实质性条款标记
    SUBSTANTIATIVE_MARKERS = ['★', '■', '●', '◆', '⚠']
    IMPORTANT_MARKERS = ['▲', '△', '▼', '▽']
    
    def __init__(self):
        self.tables: List[TableMetadata] = []
        self._table_id_counter = 0
    
    def parse_table(self, table_element) -> TableMetadata:
        """
        解析单个表格
        
        Args:
            table_element: docx表格元素
            
        Returns:
            TableMetadata: 表格元数据
        """
        table_id = self._table_id_counter
        self._table_id_counter += 1
        
        metadata = TableMetadata(table_id=table_id, raw_element=table_element)
        
        # 解析行和单元格
        rows = self._parse_rows(table_element)
        metadata.row_count = len(rows)
        
        if rows:
            metadata.col_count = max(len(row.cells) for row in rows)
        
        # 识别表格类型
        metadata.table_type = self._identify_table_type(rows)
        
        # 提取关键内容
        self._extract_critical_content(metadata, rows)
        
        # 检查实质性条款
        metadata.has_substantiative = metadata.substantiative_count > 0
        
        return metadata
    
    def parse_tables_from_document(self, doc) -> List[TableMetadata]:
        """
        从文档中解析所有表格
        
        Args:
            doc: python-docx Document 对象
            
        Returns:
            List[TableMetadata]: 表格元数据列表
        """
        self.tables = []
        self._table_id_counter = 0
        
        # 获取所有段落用于上下文关联
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        for idx, table in enumerate(doc.tables):
            metadata = self.parse_table(table)
            
            # 关联上下文
            self._link_table_to_context(metadata, paragraphs, idx)
            
            self.tables.append(metadata)
        
        return self.tables
    
    def _parse_rows(self, table_element) -> List[TableRow]:
        """解析表格行"""
        rows = []
        
        for row_idx, row in enumerate(table_element.rows):
            cells = []
            is_header_row = row_idx == 0
            
            for col_idx, cell in enumerate(row.cells):
                cell_text = cell.text if hasattr(cell, 'text') else str(cell)
                cell_type = self._classify_cell(cell_text, is_header_row)
                
                table_cell = TableCell(
                    text=cell_text,
                    row=row_idx,
                    col=col_idx,
                    cell_type=cell_type,
                    is_header=is_header_row,
                    is_substantiative='★' in cell_text
                )
                cells.append(table_cell)
            
            rows.append(TableRow(
                cells=cells,
                row_index=row_idx,
                is_header_row=is_header_row
            ))
        
        return rows
    
    def _classify_cell(self, text: str, is_header: bool) -> CellType:
        """分类单元格类型"""
        if is_header:
            return CellType.HEADER
        
        if '★' in text:
            return CellType.HIGHLIGHTED_STAR
        elif '▲' in text:
            return CellType.HIGHLIGHTED_TRIANGLE
        
        # 检查是否为实质性条款
        if any(marker in text for marker in self.SUBSTANTIATIVE_MARKERS):
            return CellType.CRITICAL
        
        return CellType.NORMAL
    
    def _identify_table_type(self, rows: List[TableRow]) -> TableType:
        """识别表格类型"""
        if not rows:
            return TableType.UNKNOWN
        
        # 收集所有文本
        all_text = ' '.join(
            cell.text for row in rows for cell in row.cells
        )
        
        # 统计各类型关键词出现次数
        type_scores = {}
        for table_type, keywords in self.TABLE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in all_text)
            type_scores[table_type] = score
        
        # 返回得分最高的类型
        if max(type_scores.values()) > 0:
            return max(type_scores, key=type_scores.get)
        
        return TableType.UNKNOWN
    
    def _extract_critical_content(self, metadata: TableMetadata, rows: List[TableRow]):
        """提取关键内容"""
        all_cells = [cell for row in rows for cell in row.cells]
        
        # 统计实质性条款数量
        metadata.substantiative_count = sum(
            1 for cell in all_cells if cell.is_substantiative
        )
        
        # 提取关键内容关键词
        critical_keywords = set()
        for cell in all_cells:
            text = cell.clean_text()
            
            # 检查关键词
            for kw in self._get_critical_keywords():
                if kw in text:
                    critical_keywords.add(kw)
        
        metadata.critical_keywords = list(critical_keywords)
    
    def _get_critical_keywords(self) -> List[str]:
        """获取关键内容关键词列表"""
        return [
            '实质性', '必须', '不得', '严禁', '禁止',
            '唯一', '指定', '限定', '专利', '专有',
            '中小企业', '小微企业', '预留份额',
            '价格扣除', '加分', '优惠'
        ]
    
    def _link_table_to_context(
        self, 
        metadata: TableMetadata, 
        paragraphs: List[str],
        table_index: int
    ):
        """将表格与上下文段落关联"""
        # 获取表格前面的段落作为标题
        if table_index > 0 and paragraphs:
            # 查找最近的非空段落
            for i in range(table_index - 1, -1, -1):
                para = paragraphs[i]
                # 跳过空行和过渡性段落
                if len(para) > 5 and not self._is_transitional(para):
                    metadata.preceding_paragraph = para
                    
                    # 尝试提取标题
                    if self._looks_like_title(para):
                        metadata.title = para
                    break
        
        # 获取表格后面的段落作为注释
        if table_index < len(paragraphs) - 1:
            next_para = paragraphs[table_index + 1]
            if len(next_para) < 200:  # 较短的可能是注释
                metadata.following_paragraph = next_para
    
    def _is_transitional(self, text: str) -> bool:
        """判断是否为过渡性段落"""
        transitional_patterns = [
            r'^\d+\.',  # 章节编号
            r'^表\d',   # 表格编号
            r'^\s*$',   # 空行
        ]
        return any(re.match(p, text) for p in transitional_patterns)
    
    def _looks_like_title(self, text: str) -> bool:
        """判断是否像标题"""
        # 简短且不以标点结尾
        if len(text) < 50 and not text.endswith(('。', '：', ':')):
            return True
        # 包含特定标题关键词
        title_keywords = ['表', '清单', '目录', '评分', '技术', '资质']
        return any(kw in text for kw in title_keywords)
    
    def extract_scoring_standard(self, table: TableMetadata) -> Optional[Dict[str, Any]]:
        """
        提取评分标准信息
        
        适用于评分标准表的特殊解析
        """
        if table.table_type != TableType.SCORING_STANDARD:
            return None
        
        result = {
            'total_score': 0,
            'items': []
        }
        
        for row in self._get_raw_rows(table):
            cells = row.cells
            
            # 尝试解析评分项
            if len(cells) >= 2:
                item = {
                    'name': cells[0].clean_text(),
                    'score': self._extract_score(cells[1].text) if len(cells) > 1 else 0,
                    'is_substantiative': '★' in cells[0].text
                }
                
                if item['name']:
                    result['items'].append(item)
                    result['total_score'] += item['score']
        
        return result
    
    def _extract_score(self, text: str) -> int:
        """从文本中提取分值"""
        # 匹配各种格式的分值
        patterns = [
            r'(\d+)\s*分',      # XX分
            r'分值?\s*[:：]?\s*(\d+)',  # 分值:XX 或 分 XX
            r'满分?\s*(\d+)',   # 满分XX
            r'(\d+)',           # 纯数字
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _get_raw_rows(self, table: TableMetadata) -> List[TableRow]:
        """从原始元素获取行数据"""
        if not table.raw_element:
            return []
        
        rows = []
        for row_idx, row in enumerate(table.raw_element.rows):
            cells = []
            for col_idx, cell in enumerate(row.cells):
                table_cell = TableCell(
                    text=cell.text if hasattr(cell, 'text') else str(cell),
                    row=row_idx,
                    col=col_idx,
                    cell_type=self._classify_cell(cell.text if hasattr(cell, 'text') else '', False)
                )
                cells.append(table_cell)
            rows.append(TableRow(cells=cells, row_index=row_idx))
        
        return rows
    
    def check_cross_table_consistency(
        self, 
        tables: List[TableMetadata]
    ) -> List[Dict[str, Any]]:
        """
        检查跨表格数据一致性
        
        例如：技术需求表中的参数与评分标准表中的参数是否一致
        """
        issues = []
        
        # 收集所有表格中的关键参数
        all_params = {}
        for table in tables:
            if table.table_type == TableType.TECHNICAL_REQUIREMENT:
                for kw in table.critical_keywords:
                    if kw not in all_params:
                        all_params[kw] = []
                    all_params[kw].append(table.table_id)
        
        # 检查评分标准表中的参数是否在技术需求表中
        for table in tables:
            if table.table_type == TableType.SCORING_STANDARD:
                for kw in table.critical_keywords:
                    if kw not in all_params:
                        issues.append({
                            'type': 'cross_table_inconsistency',
                            'severity': 'warning',
                            'message': f'评分标准中的参数 "{kw}" 未在技术需求表中定义',
                            'table_id': table.table_id
                        })
        
        return issues
    
    def generate_table_summary(self, tables: List[TableMetadata]) -> Dict[str, Any]:
        """生成表格解析摘要"""
        summary = {
            'total_tables': len(tables),
            'by_type': {},
            'substantiative_count': 0,
            'critical_keywords': set()
        }
        
        for table in tables:
            # 按类型统计
            type_name = table.table_type.value
            summary['by_type'][type_name] = summary['by_type'].get(type_name, 0) + 1
            
            # 统计实质性条款
            summary['substantiative_count'] += table.substantiative_count
            
            # 收集关键词
            summary['critical_keywords'].update(table.critical_keywords)
        
        summary['critical_keywords'] = list(summary['critical_keywords'])
        
        return summary
