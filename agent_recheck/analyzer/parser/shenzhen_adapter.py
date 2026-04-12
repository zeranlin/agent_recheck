"""深圳格式适配器"""

import re
from typing import Optional

from models.document import MarkedContent
from utils.logging import get_logger

logger = get_logger("parser.shenzhen_adapter")


class ShenzhenAdapter:
    """
    深圳政府采购格式适配器

    深圳招标文件有以下特点：
    1. 使用 ★ 标记实质性条款
    2. 使用 ▲ 标记重要参数
    3. 章节结构：第一章、第二章...
    4. 专用条款 + 通用条款结构
    """

    def __init__(self):
        self.substantive_mark = "★"
        self.important_mark = "▲"

    def adapt(self, marked_contents: list[MarkedContent], full_text: str) -> list[MarkedContent]:
        """
        适配深圳格式

        Args:
            marked_contents: 已提取的标记内容
            full_text: 全文

        Returns:
            适配后的标记内容
        """
        # 如果已经识别了标记，直接返回
        if marked_contents:
            return marked_contents

        # 从正文中重新识别
        lines = full_text.split("\n")
        adapted = []

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            # 识别实质性条款
            if self.substantive_mark in line:
                adapted.append(
                    MarkedContent(
                        type="实质性",
                        content=self._clean_marked_text(line, self.substantive_mark),
                        line=line_num,
                        context=line[:200],
                    )
                )

            # 识别重要参数
            if self.important_mark in line:
                adapted.append(
                    MarkedContent(
                        type="重要参数",
                        content=self._clean_marked_text(line, self.important_mark),
                        line=line_num,
                        context=line[:200],
                    )
                )

        logger.info("shenzhen_adapter_applied", marked_count=len(adapted))
        return adapted

    def _clean_marked_text(self, text: str, mark: str) -> str:
        """清理标记文本"""
        # 移除标记符号
        cleaned = text.replace(mark, "").strip()
        return cleaned

    def extract_structural_marks(self, text: str) -> dict:
        """
        提取结构性标记

        深圳文档常见的结构性标记：
        - ★：实质性条款（不可负偏离）
        - ▲：重要参数（负偏离重点扣分）
        """
        marks = {
            "substantive": [],  # 实质性条款
            "important": [],     # 重要参数
        }

        lines = text.split("\n")
        for line_num, line in enumerate(lines, start=1):
            if self.substantive_mark in line:
                marks["substantive"].append({
                    "line": line_num,
                    "content": self._clean_marked_text(line, self.substantive_mark),
                })

            if self.important_mark in line:
                marks["important"].append({
                    "line": line_num,
                    "content": self._clean_marked_text(line, self.important_mark),
                })

        return marks

    def is_shenzhen_format(self, text: str) -> bool:
        """
        判断是否是深圳格式文档

        检测特征：
        1. 包含深圳经济特区政府采购条例
        2. 包含专用条款/通用条款结构
        """
        shenzhen_indicators = [
            "深圳经济特区政府采购条例",
            "专用条款",
            "通用条款",
            "投标及履约承诺函",
        ]

        indicator_count = sum(1 for ind in shenzhen_indicators if ind in text)
        return indicator_count >= 2
