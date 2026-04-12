"""PDF 文档解析器"""

from pathlib import Path
from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DocumentMetadata:
    """文档元数据"""
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    file_type: str = "pdf"
    page_count: int = 0
    paragraph_count: int = 0
    table_count: int = 0


@dataclass
class DocumentSection:
    """文档章节"""
    title: str = ""
    level: int = 1
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
    page: int = 0
    is_nested: bool = False


@dataclass
class Document:
    """文档对象"""
    metadata: Optional[DocumentMetadata] = None
    full_text: str = ""
    sections: List[DocumentSection] = field(default_factory=list)
    tables: List[Any] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    parsed_at: datetime = field(default_factory=datetime.now)


class PdfParser:
    """PDF 文档解析器"""

    def __init__(self):
        pass

    def parse(self, file_path: Path) -> Document:
        """解析 PDF 文件"""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

        with pdfplumber.open(file_path) as pdf:
            metadata = self._extract_metadata(file_path, pdf)
            full_text = self.extract_text(file_path)
            paragraphs = self._extract_paragraphs(file_path)
            tables = self._extract_tables(file_path)

        return Document(
            metadata=metadata,
            full_text=full_text,
            sections=[],
            tables=tables,
            paragraphs=paragraphs,
        )

    def extract_text(self, file_path: Path) -> str:
        """提取纯文本"""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def extract_tables(self, file_path: Path) -> List[dict]:
        """提取表格"""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

        tables = []
        table_index = 0

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_tables = page.extract_tables()
                for table_data in page_tables:
                    if table_data:
                        tables.append({
                            "index": table_index,
                            "page": page_num,
                            "data": table_data,
                            "rows": len(table_data),
                            "cols": len(table_data[0]) if table_data else 0,
                        })
                        table_index += 1

        return tables

    def _extract_metadata(self, file_path: Path, pdf) -> DocumentMetadata:
        """提取元数据"""
        page_count = len(pdf.pages)
        return DocumentMetadata(
            file_path=str(file_path),
            file_name=file_path.name,
            file_size=file_path.stat().st_size if file_path.exists() else 0,
            file_type="pdf",
            page_count=page_count,
            paragraph_count=0,
            table_count=0,
        )

    def _extract_paragraphs(self, file_path: Path) -> List[str]:
        """提取段落"""
        text = self.extract_text(file_path)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        return paragraphs
