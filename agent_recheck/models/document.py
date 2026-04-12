# -*- coding: utf-8 -*-
"""
文档数据模型
"""

from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DocumentMetadata:
    """文档元数据"""
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    file_type: str = ""
    page_count: int = 0
    paragraph_count: int = 0
    table_count: int = 0


@dataclass
class DocumentSection:
    """文档章节"""
    title: str = ""
    level: int = 1
    start_line: int = 0
    end_line: int = 0
    start_page: int = 0
    end_page: int = 0
    content: str = ""


@dataclass
class TableInfo:
    """表格信息"""
    index: int = 0
    title: Optional[str] = None
    rows: int = 0
    cols: int = 0
    start_line: int = 0
    end_line: int = 0
    page: int = 0
    is_nested: bool = False


@dataclass
class MarkedContent:
    """标记内容"""
    type: str = ""
    content: str = ""
    line: int = 0
    context: str = ""


@dataclass
class Document:
    """文档对象"""
    metadata: Optional[DocumentMetadata] = None
    full_text: str = ""
    sections: List[DocumentSection] = field(default_factory=list)
    tables: List[Any] = field(default_factory=list)
    marked_contents: List[MarkedContent] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    parsed_at: datetime = field(default_factory=datetime.now)


# 向后兼容别名
ParsedDocument = Document
ParsedSection = DocumentSection
ParsedParagraph = str
