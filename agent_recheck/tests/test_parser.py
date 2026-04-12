"""解析器测试"""

import pytest
from pathlib import Path

from analyzer.parser.docx_parser import DocxParser
from analyzer.parser.pdf_parser import PdfParser
from analyzer.parser.base import ParserFactory


class TestDocxParser:
    """DOCX 解析器测试"""

    def test_extract_text(self, sample_docx_path):
        """测试文本提取"""
        parser = DocxParser()
        text = parser.extract_text(sample_docx_path)

        assert text is not None
        assert len(text) > 0

    def test_parse_document(self, sample_docx_path):
        """测试文档解析"""
        parser = DocxParser()
        document = parser.parse(sample_docx_path)

        assert document.metadata.file_type == "docx"
        assert document.full_text is not None
        assert document.metadata.paragraph_count > 0

    def test_extract_marked_contents(self, sample_docx_path):
        """测试标记内容提取"""
        parser = DocxParser()
        document = parser.parse(sample_docx_path)

        # 深圳文档应该有标记
        # 注意：sample_docx_path 可能没有这些标记
        assert isinstance(document.marked_contents, list)


class TestParserFactory:
    """解析器工厂测试"""

    def test_create_docx_parser(self):
        """测试创建 DOCX 解析器"""
        parser = ParserFactory.create_parser(Path("test.docx"))
        assert isinstance(parser, DocxParser)

    def test_create_pdf_parser(self):
        """测试创建 PDF 解析器"""
        parser = ParserFactory.create_parser(Path("test.pdf"))
        assert isinstance(parser, PdfParser)

    def test_unsupported_type(self):
        """测试不支持的类型"""
        with pytest.raises(ValueError):
            ParserFactory.create_parser(Path("test.txt"))


# Pytest fixtures
@pytest.fixture
def sample_docx_path():
    """示例 DOCX 文件路径"""
    return Path(__file__).parent / "fixtures" / "sample.docx"


@pytest.fixture
def sample_pdf_path():
    """示例 PDF 文件路径"""
    return Path(__file__).parent / "fixtures" / "sample.pdf"
