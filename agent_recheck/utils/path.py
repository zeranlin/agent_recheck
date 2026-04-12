"""路径工具类"""

import os
from pathlib import Path
from typing import Union


class PathUtils:
    """路径工具类"""

    @staticmethod
    def get_project_root() -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent.parent

    @staticmethod
    def get_config_dir() -> Path:
        """获取配置目录"""
        return PathUtils.get_project_root() / "config"

    @staticmethod
    def get_knowledge_dir() -> Path:
        """获取知识库目录"""
        return PathUtils.get_project_root() / "knowledge"

    @staticmethod
    def get_rules_dir() -> Path:
        """获取规则目录"""
        return PathUtils.get_project_root() / "agent_recheck" / "rules"

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """
        确保目录存在，不存在则创建

        Args:
            path: 目录路径

        Returns:
            目录 Path 对象
        """
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def get_relative_path(path: Union[str, Path], base: Union[str, Path]) -> Path:
        """
        获取相对路径

        Args:
            path: 目标路径
            base: 基准路径

        Returns:
            相对路径
        """
        return Path(path).relative_to(base)

    @staticmethod
    def expand_path(path: Union[str, Path]) -> Path:
        """
        展开路径（支持 ~ 和环境变量）

        Args:
            path: 路径

        Returns:
            展开后的 Path 对象
        """
        return Path(os.path.expandvars(os.path.expanduser(str(path))))

    @staticmethod
    def is_supported_file(path: Union[str, Path]) -> bool:
        """
        检查文件是否支持解析

        Args:
            path: 文件路径

        Returns:
            是否支持
        """
        suffix = Path(path).suffix.lower()
        return suffix in [".docx", ".doc", ".pdf"]
