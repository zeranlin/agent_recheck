"""LLM 客户端"""

import asyncio
from typing import Optional

from ...utils.logging import get_logger

logger = get_logger("llm.client")


class LLMClient:
    """
    LLM 客户端封装

    支持：
    - 自有 qwen3.5-27b
    - OpenAI 兼容 API
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.model = self.config.get("model", "qwen3.5-27b")
        self.api_base = self.config.get("api_base", "http://112.111.54.86:10011/v1")
        self.api_key = self.config.get("api_key", "1212")
        self.timeout = self.config.get("timeout", 60)
        self.max_retries = self.config.get("max_retries", 3)

        # 延迟初始化 client
        self._client = None

    @property
    def client(self):
        """懒加载客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    base_url=self.api_base,
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            except ImportError:
                logger.warning("openai_package_not_installed")
                return None
        return self._client

    @classmethod
    def from_config_file(cls, config_path: Optional[str] = None) -> "LLMClient":
        """从配置文件加载"""
        import yaml
        import os
        
        if config_path is None:
            # 查找默认配置
            possible_paths = [
                "agent_recheck/config/default.yaml",
                "config/default.yaml",
                os.path.expanduser("~/.agent_recheck/config.yaml"),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return cls(config.get("llm", {}))
        
        return cls({})

    async def is_available(self, timeout: float = 5) -> bool:
        """检查 LLM 服务是否可用"""
        if not self.client:
            return False

        try:
            await asyncio.wait_for(
                self.client.models.list(),
                timeout=timeout,
            )
            return True
        except asyncio.TimeoutError:
            logger.warning("llm_health_check_timeout")
            return False
        except Exception as e:
            logger.warning("llm_health_check_failed", error=str(e))
            return False

    async def analyze(self, document, prompt: Optional[str] = None) -> list:
        """
        使用 LLM 分析文档

        Args:
            document: 文档对象
            prompt: 自定义提示词

        Returns:
            发现的问题列表
        """
        from .prompts import PromptTemplates

        if not prompt:
            prompt = PromptTemplates.get_analysis_prompt()

        # 构建完整提示词
        full_prompt = prompt.format(
            document_title=document.metadata.file_name,
            document_content=document.full_text[:8000],  # 限制长度
        )

        try:
            response = await self._call_with_retry(full_prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error("llm_analysis_failed", error=str(e))
            raise

    async def _call_with_retry(self, prompt: str, retries: int = 0) -> str:
        """带重试的调用"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的政府采购招投标文件合规审查专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            return response.choices[0].message.content

        except asyncio.TimeoutError:
            if retries < self.max_retries:
                logger.warning("llm_timeout_retry", retry=retries + 1)
                return await self._call_with_retry(prompt, retries + 1)
            raise

        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            raise

    def _parse_response(self, response: str) -> list:
        """解析 LLM 响应"""
        # 期望返回 JSON 格式
        import json
        import re

        # 尝试提取 JSON
        json_match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return self._convert_to_issues(data)
                elif isinstance(data, dict) and "issues" in data:
                    return self._convert_to_issues(data["issues"])
            except json.JSONDecodeError:
                pass

        # 如果不是 JSON，记录警告
        logger.warning("llm_response_not_json", response=response[:200])
        return []

    def _convert_to_issues(self, items: list) -> list:
        """将字典转换为 Issue 对象"""
        from models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion

        issues = []
        for item in items:
            try:
                location = IssueLocation(
                    line_start=item.get("line", 0),
                    line_end=item.get("line", 0),
                )

                evidence = IssueEvidence(
                    quote=item.get("quote", ""),
                    location=location,
                )

                rule = IssueRule(
                    id=item.get("rule_id", "LLM"),
                    name=item.get("rule_name", "LLM识别"),
                    reference=item.get("reference", ""),
                )

                suggestion = IssueSuggestion(
                    content=item.get("suggestion", ""),
                )

                issue = Issue(
                    id=f"llm_{len(issues)}",
                    type="LLM识别",
                    category=item.get("category", "其他"),
                    level=item.get("level", "medium"),
                    title=item.get("title", "发现问题"),
                    evidence=evidence,
                    rule=rule,
                    suggestion=suggestion,
                    confidence=item.get("confidence", 0.7),
                    source="llm",
                )

                issues.append(issue)
            except Exception as e:
                logger.warning("issue_conversion_failed", error=str(e))

        return issues
