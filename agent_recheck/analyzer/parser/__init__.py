"""文档解析器模块"""

from .base import BaseParser, ParserFactory
from .docx_parser import DocxParser
from .pdf_parser import PdfParser
from .enhanced_table_parser import (
    EnhancedTableParser,
    TableMetadata,
    TableCell,
    TableRow,
    CellType,
    TableType,
)
from .shenzhen_adapter import ShenzhenAdapter

__all__ = [
    # 基础解析
    "BaseParser",
    "ParserFactory",
    "DocxParser",
    "PdfParser",
    "ShenzhenAdapter",
    # 表格解析
    "EnhancedTableParser",
    "TableMetadata",
    "TableCell",
    "TableRow",
    "CellType",
    "TableType",
]
