"""文档数据模型"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """文档元数据"""
    file_path: str
    file_name: str
    file_size: int
    file_type: str  # docx, pdf
    parsed_at: datetime = Field(default_factory=datetime.now)
    page_count: Optional[int] = None
    paragraph_count: int = 0
    table_count: int = 0


class DocumentSection(BaseModel):
    """文档章节"""
    title: str
    level: int  # 1=章, 2=节, 3=条
    start_line: int
    end_line: int
    content: str


class TableInfo(BaseModel):
    """表格信息"""
    index: int
    title: Optional[str] = None
    rows: int
    cols: int
    start_line: int
    end_line: int
    is_nested: bool = False


class MarkedContent(BaseModel):
    """标记内容（★ 和 ▲）"""
    type: str  # "实质性" 或 "重要参数"
    content: str
    line: int
    context: str


class Document(BaseModel):
    """文档模型"""
    metadata: DocumentMetadata
    full_text: str
    sections: list[DocumentSection] = []
    tables: list[TableInfo] = []
    marked_contents: list[MarkedContent] = []

    def get_section_at_line(self, line: int) -> Optional[DocumentSection]:
        """获取指定行所属的章节"""
        for section in self.sections:
            if section.start_line <= line <= section.end_line:
                return section
        return None

    def get_table_at_line(self, line: int) -> Optional[TableInfo]:
        """获取包含指定行的表格"""
        for table in self.tables:
            if table.start_line <= line <= table.end_line:
                return table
        return None
