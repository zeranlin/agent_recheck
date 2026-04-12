"""文档解析器模块"""

from .base import BaseParser, ParserFactory
from .docx_parser import DocxParser
from .pdf_parser import PdfParser

__all__ = [
    "BaseParser",
    "ParserFactory",
    "DocxParser",
    "PdfParser",
]
