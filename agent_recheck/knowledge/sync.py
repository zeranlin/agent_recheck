"""知识库同步工具"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from utils.logging import get_logger
from utils.path import PathUtils

logger = get_logger("knowledge.sync")


class KnowledgeSync:
    """知识库同步工具"""

    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or PathUtils.get_knowledge_dir()

    def get_regulations_status(self) -> list[dict]:
        """获取法规状态"""
        regulations = []

        # 加载国家法规
        national_dir = self.knowledge_dir / "regulations" / "national"
        if national_dir.exists():
            for reg_file in national_dir.glob("*.md"):
                regulations.append({
                    "name": reg_file.stem,
                    "path": str(reg_file),
                    "status": "effective",
                    "version": self._get_file_version(reg_file),
                })

        # 加载深圳法规
        shenzhen_dir = self.knowledge_dir / "regulations" / "shenzhen"
        if shenzhen_dir.exists():
            for reg_file in shenzhen_dir.glob("*.md"):
                regulations.append({
                    "name": reg_file.stem,
                    "path": str(reg_file),
                    "status": "effective",
                    "version": self._get_file_version(reg_file),
                    "region": "深圳",
                })

        return regulations

    def sync_all(self) -> dict:
        """同步所有知识库"""
        result = {
            "updated": 0,
            "added": 0,
            "errors": [],
        }

        # 这里可以实现从远程同步的逻辑
        # 目前是占位实现

        logger.info("knowledge_sync_completed", result=result)
        return result

    def export(self, output_dir: Path):
        """导出知识库"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 复制所有法规文件
        regulations_dir = self.knowledge_dir / "regulations"
        if regulations_dir.exists():
            import shutil
            dest = output_dir / "regulations"
            shutil.copytree(regulations_dir, dest, dirs_exist_ok=True)

        logger.info("knowledge_exported", output=str(output_dir))

    def _get_file_version(self, file_path: Path) -> str:
        """获取文件版本"""
        try:
            stat = file_path.stat()
            return datetime.fromtimestamp(stat.st_mtime).strftime("%Y%m%d")
        except Exception:
            return "unknown"
