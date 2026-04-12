"""DOCX 文档解析器"""

import re
from pathlib import Path
from typing import Optional

from docx import Document as DocxDocument
from docx.table import Table as DocxTable

from models.document import (
    Document,
    DocumentMetadata,
    DocumentSection,
    TableInfo,
    MarkedContent,
)
from utils.logging import get_logger

from .base import BaseParser
from .shenzhen_adapter import ShenzhenAdapter

logger = get_logger("parser.docx")


class DocxParser(BaseParser):
    """DOCX 文档解析器"""

    def __init__(self):
        self.shenzhen_adapter = ShenzhenAdapter()

    def parse(self, file_path: Path) -> Document:
        """解析 DOCX 文件"""
        doc = DocxDocument(file_path)

        # 提取元数据
        metadata = self._extract_metadata(file_path, doc)

        # 提取全文
        full_text = self.extract_text(file_path)

        # 提取章节
        sections = self._extract_sections(doc)

        # 提取表格
        tables = self._extract_tables(doc)

        # 提取标记内容（★ 和 ▲）
        marked_contents = self._extract_marked_contents(doc)

        # 应用深圳格式适配
        marked_contents = self.shenzhen_adapter.adapt(marked_contents, full_text)

        return Document(
            metadata=metadata,
            full_text=full_text,
            sections=sections,
            tables=tables,
            marked_contents=marked_contents,
        )

    def extract_text(self, file_path: Path) -> str:
        """提取纯文本"""
        doc = DocxDocument(file_path)
        paragraphs = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        return "\n".join(paragraphs)

    def extract_tables(self, file_path: Path) -> list[dict]:
        """提取表格"""
        doc = DocxDocument(file_path)
        tables = []

        for i, table in enumerate(doc.tables):
            table_data = self._parse_table(table)
            table_data["index"] = i
            tables.append(table_data)

        return tables

    def _extract_metadata(self, file_path: Path, doc: DocxDocument) -> DocumentMetadata:
        """提取元数据"""
        return DocumentMetadata(
            file_path=str(file_path),
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            file_type="docx",
            paragraph_count=len([p for p in doc.paragraphs if p.text.strip()]),
            table_count=len(doc.tables),
        )

    def _extract_sections(self, doc: DocxDocument) -> list[DocumentSection]:
        """提取章节结构"""
        sections = []
        current_line = 0

        # 章节标题模式
        chapter_pattern = re.compile(r"^第[一二三四五六七八九十百\d]+[章节条]")
        section_pattern = re.compile(r"^[一二三四五六七八九十]+、")
        article_pattern = re.compile(r"^\d+[.、]")

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                current_line += 1
                continue

            level = 0
            if chapter_pattern.match(text):
                level = 1
            elif section_pattern.match(text):
                level = 2
            elif article_pattern.match(text):
                level = 3

            if level > 0:
                sections.append(
                    DocumentSection(
                        title=text[:80],
                        level=level,
                        start_line=current_line,
                        end_line=current_line,
                        content=text,
                    )
                )

            current_line += 1

        return sections

    def _extract_tables(self, doc: DocxDocument) -> list[TableInfo]:
        """提取表格信息"""
        tables = []

        for i, table in enumerate(doc.tables):
            table_info = self._parse_table_info(table, i)
            if table_info:
                tables.append(table_info)

        return tables

    def _parse_table_info(self, table: DocxTable, index: int) -> Optional[TableInfo]:
        """解析表格信息"""
        rows = len(table.rows)
        cols = len(table.columns) if rows > 0 else 0

        # 检查是否是嵌套表格
        is_nested = rows < 2 or cols < 2

        # 尝试提取标题
        title = None
        if rows > 0:
            first_cell = table.cell(0, 0).text.strip()
            if first_cell:
                title = first_cell[:50]

        return TableInfo(
            index=index,
            title=title,
            rows=rows,
            cols=cols,
            start_line=0,  # 简化处理
            end_line=0,
            is_nested=is_nested,
        )

    def _extract_marked_contents(self, doc: DocxDocument) -> list[MarkedContent]:
        """提取标记内容（★ 和 ▲）"""
        marked = []
        line = 0

        for para in doc.paragraphs:
            text = para.text
            line += 1

            # 提取 ★ 标记
            if "★" in text:
                marked.append(
                    MarkedContent(
                        type="实质性",
                        content=text.strip(),
                        line=line,
                        context=text.strip()[:200],
                    )
                )

            # 提取 ▲ 标记
            if "▲" in text:
                marked.append(
                    MarkedContent(
                        type="重要参数",
                        content=text.strip(),
                        line=line,
                        context=text.strip()[:200],
                    )
                )

        return marked

    def _parse_table(self, table: DocxTable) -> dict:
        """解析表格内容"""
        data = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            data.append(row_data)
        return {"data": data}
