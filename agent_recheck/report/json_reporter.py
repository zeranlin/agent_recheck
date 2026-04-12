"""JSON 报告生成器"""

import json
from pathlib import Path
from typing import Union

from ..models.report import AnalysisReport
from ..utils.logging import get_logger

logger = get_logger("report.json")


class JsonReporter:
    """JSON 报告生成器"""

    def save(self, report: AnalysisReport, output: Union[str, Path]):
        """
        保存报告为 JSON

        Args:
            report: 分析报告
            output: 输出路径
        """
        output = Path(output)

        data = report.model_dump(mode="json")

        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("json_report_saved", output=str(output))
