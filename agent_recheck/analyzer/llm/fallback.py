"""LLM 容错处理"""

from utils.logging import get_logger

logger = get_logger("llm.fallback")


class LLMFallback:
    """LLM 容错处理"""

    def handle_failure(self, error: Exception, document) -> list:
        """
        处理 LLM 调用失败

        Args:
            error: 异常
            document: 文档对象

        Returns:
            空列表（降级到纯规则模式）
        """
        error_type = type(error).__name__

        if "TimeoutError" in error_type or "asyncio.TimeoutError" in str(error_type):
            logger.warning("llm_timeout_fallback")
        elif "ConnectionError" in error_type:
            logger.warning("llm_connection_fallback")
        else:
            logger.error("llm_unknown_error_fallback", error=str(error))

        # 返回空列表，由规则引擎兜底
        return []

    def get_fallback_message(self, error: Exception) -> str:
        """获取降级消息"""
        error_type = type(error).__name__

        messages = {
            "TimeoutError": "LLM 分析超时，已切换到规则引擎模式",
            "ConnectionError": "LLM 服务不可用，已切换到规则引擎模式",
            "RateLimitError": "LLM 请求频率限制，已切换到规则引擎模式",
        }

        return messages.get(error_type, "LLM 分析失败，已切换到规则引擎模式")
