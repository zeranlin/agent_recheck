"""PDF 文档解析器"""

from pathlib import Path

import pdfplumber

from models.document import (
    Document,
    DocumentMetadata,
    TableInfo,
)
from utils.logging import get_logger

from .base import BaseParser

logger = get_logger("parser.pdf")


class PdfParser(BaseParser):
    """PDF 文档解析器"""

    def parse(self, file_path: Path) -> Document:
        """解析 PDF 文件"""
        metadata = self._extract_metadata(file_path)
        full_text = self.extract_text(file_path)
        tables = self._extract_tables(file_path)

        return Document(
            metadata=metadata,
            full_text=full_text,
            sections=[],  # PDF 章节提取较复杂，后续优化
            tables=tables,
            marked_contents=[],  # PDF 标记提取后续优化
        )

    def extract_text(self, file_path: Path) -> str:
        """提取纯文本"""
        texts = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)

        return "\n".join(texts)

    def extract_tables(self, file_path: Path) -> list[dict]:
        """提取表格"""
        tables = []

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                for j, table in enumerate(page_tables):
                    tables.append({
                        "page": i + 1,
                        "index": j,
                        "data": table,
                    })

        return tables

    def _extract_metadata(self, file_path: Path) -> DocumentMetadata:
        """提取元数据"""
        metadata = DocumentMetadata(
            file_path=str(file_path),
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            file_type="pdf",
        )

        try:
            with pdfplumber.open(file_path) as pdf:
                metadata.page_count = len(pdf.pages)
        except Exception as e:
            logger.warning("failed_to_get_page_count", error=str(e))

        return metadata
