"""文档解析器基类"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type

from models.document import Document


class BaseParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    def parse(self, file_path: Path) -> Document:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            Document 对象
        """
        pass

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """
        提取纯文本

        Args:
            file_path: 文件路径

        Returns:
            纯文本内容
        """
        pass

    @abstractmethod
    def extract_tables(self, file_path: Path) -> list[dict]:
        """
        提取表格

        Args:
            file_path: 文件路径

        Returns:
            表格列表
        """
        pass


class ParserFactory:
    """解析器工厂"""

    _parsers: dict[str, Type[BaseParser]] = {}

    @classmethod
    def register(cls, file_type: str, parser_class: Type[BaseParser]):
        """注册解析器"""
        cls._parsers[file_type] = parser_class

    @classmethod
    def create_parser(cls, file_path: Path) -> BaseParser:
        """
        创建解析器

        Args:
            file_path: 文件路径

        Returns:
            对应的解析器实例
        """
        suffix = file_path.suffix.lower().lstrip(".")

        if suffix not in cls._parsers:
            raise ValueError(f"不支持的文件类型: {suffix}")

        return cls._parsers[suffix]()

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """获取支持的文件类型"""
        return list(cls._parsers.keys())


# 注册默认解析器
from .docx_parser import DocxParser
from .pdf_parser import PdfParser

ParserFactory.register("docx", DocxParser)
ParserFactory.register("doc", DocxParser)
ParserFactory.register("pdf", PdfParser)
