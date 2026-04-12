"""安全工具类"""

import os
import re
from typing import Any


class SecurityUtils:
    """安全工具类"""

    @staticmethod
    def mask_api_key(key: str) -> str:
        """
        API Key 脱敏：显示前4位

        Args:
            key: API Key

        Returns:
            脱敏后的 Key
        """
        if not key:
            return "****"
        if len(key) <= 4:
            return "****"
        return key[:4] + "****"

    @staticmethod
    def mask_file_path(path: str) -> str:
        """
        文件路径脱敏：隐藏用户目录

        Args:
            path: 文件路径

        Returns:
            脱敏后的路径
        """
        home = os.path.expanduser("~")
        return path.replace(home, "~")

    @staticmethod
    def sanitize_log(data: dict[str, Any]) -> dict[str, Any]:
        """
        日志数据脱敏

        Args:
            data: 日志数据字典

        Returns:
            脱敏后的字典
        """
        sensitive_fields = ["api_key", "password", "token", "secret", "credential"]

        result = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                if isinstance(value, str):
                    result[key] = SecurityUtils.mask_api_key(value)
                else:
                    result[key] = "****"
            elif isinstance(value, dict):
                result[key] = SecurityUtils.sanitize_log(value)
            else:
                result[key] = value

        return result

    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏：显示前3后4位"""
        if not phone or len(phone) < 7:
            return "****"
        return phone[:3] + "****" + phone[-4:]

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证脱敏：显示前3后4位"""
        if not id_card or len(id_card) < 7:
            return "****"
        return id_card[:3] + "***********" + id_card[-4:]
