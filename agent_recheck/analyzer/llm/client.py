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
        self.timeout = self.config.get("timeout", 300)  # 增加超时到 5 分钟
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
            import traceback
            tb = traceback.format_exc()
            logger.error("llm_analysis_failed", error=str(e), traceback=tb)
            print(f"DEBUG: Exception in analyze: {e}\n{tb}")
            raise

    async def _call_with_retry(self, prompt: str, retries: int = 0) -> str:
        """带重试的调用"""
        import re
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的政府采购招投标文件合规审查专家。\n\n核心原则：只报告明确的、确凿的违规问题，宁缺毋滥。\n\n你必须严格遵循以下规则：\n1. 只输出JSON数组格式，不要输出任何其他文字\n2. 每个问题必须包含title、description、level、category、suggestion字段\n3. 如果没有发现问题或问题不明显，返回空数组[]\n4. 不要输出任何思考过程、解释或说明\n5. 禁止输出任何非JSON内容\n6. 只报告有明确证据支持的违规问题，不要猜测或过度解读"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=8000,  # 增加 max_tokens 避免截断
                extra_body={"reasoning_depth": 0},  # 禁用思考模式
            )

            message = response.choices[0].message
            
            # 优先使用 content 字段
            content = message.content
            
            # 记录原始响应用于调试
            if content:
                logger.info("llm_content_received", content_preview=content[:200])
            
            # 如果 content 为空或为空字符串，从 reasoning 字段提取最终JSON输出
            if not content and hasattr(message, 'reasoning') and message.reasoning:
                reasoning = message.reasoning
                
                # 从 reasoning 末尾提取 JSON（模型通常在末尾输出结论）
                # 策略1：查找代码块
                code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', reasoning, re.DOTALL)
                for block in reversed(code_blocks):
                    block = block.strip()
                    if block and len(block) > 20:
                        try:
                            import json as json_lib
                            json_lib.loads(block)
                            content = block
                            break
                        except:
                            continue
                
                # 策略2：从 reasoning 末尾提取可能的 JSON
                if not content:
                    # 尝试匹配 JSON 数组或对象
                    last_part = reasoning[-3000:]  # 取最后 3000 字符
                    
                    # 查找可能的 JSON 开始位置
                    for match in re.finditer(r'[\[\{]', last_part):
                        start_pos = match.start()
                        potential = last_part[start_pos:]
                        
                        # 尝试找到匹配的结束括号
                        if potential.startswith('['):
                            # JSON 数组
                            depth = 0
                            for i, c in enumerate(potential):
                                if c == '[':
                                    depth += 1
                                elif c == ']':
                                    depth -= 1
                                    if depth == 0:
                                        try:
                                            import json as json_lib
                                            test_json = potential[:i+1]
                                            json_lib.loads(test_json)
                                            content = test_json
                                            break
                                        except:
                                            pass
                        elif potential.startswith('{'):
                            # JSON 对象
                            depth = 0
                            for i, c in enumerate(potential):
                                if c == '{':
                                    depth += 1
                                elif c == '}':
                                    depth -= 1
                                    if depth == 0:
                                        try:
                                            import json as json_lib
                                            test_json = potential[:i+1]
                                            json_lib.loads(test_json)
                                            content = test_json
                                            break
                                        except:
                                            pass
                        if content:
                            break
            
            return content if content else ""

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
        import json
        import re

        # 尝试提取 JSON - 查找完整的JSON数组或对象
        # 策略1：查找代码块
        code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', response, re.DOTALL)
        for block in code_blocks:
            block = block.strip()
            if block and len(block) > 10:
                try:
                    data = json.loads(block)
                    if isinstance(data, list) and len(data) > 0:
                        return self._convert_to_issues(data)
                    elif isinstance(data, dict):
                        return self._parse_dict_response(data)
                except json.JSONDecodeError:
                    pass

        # 策略2：查找JSON数组 [...] 
        # 先尝试直接解析整个响应（可能被截断但仍是有效JSON前缀）
        try:
            data = json.loads(response)
            if isinstance(data, list) and len(data) > 0:
                return self._convert_to_issues(data)
            elif isinstance(data, dict):
                return self._parse_dict_response(data)
        except json.JSONDecodeError:
            pass
        
        # 策略2.5：智能处理截断的JSON数组 - 提取所有完整的JSON对象
        try:
            array_start = response.find('[')
            if array_start != -1:
                array_content = response[array_start:]
                
                # 方法A：逐个提取所有完整的JSON对象
                objects = []
                depth = 0
                current_obj = ""
                in_string = False
                escape_next = False
                
                for i, char in enumerate(array_content):
                    if escape_next:
                        escape_next = False
                        current_obj += char
                        continue
                    if char == '\\':
                        escape_next = True
                        current_obj += char
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        current_obj += char
                        continue
                    
                    if not in_string:
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                        current_obj += char
                        
                        # 如果depth回到0且有内容，尝试解析一个完整对象
                        if depth == 0 and current_obj.strip():
                            try:
                                obj = json.loads(current_obj)
                                objects.append(obj)
                                current_obj = ""  # 重置，准备收集下一个对象
                            except json.JSONDecodeError:
                                # 被截断了，停止收集
                                break
                    else:
                        current_obj += char
                
                if len(objects) > 0:
                    logger.info("extracted_multiple_objects", count=len(objects))
                    return self._convert_to_issues(objects)
                
                # 没有找到多个完整对象，尝试直接提取第一个完整对象
                brace_start = response.find('{')
                if brace_start != -1:
                    brace_content = response[brace_start:]
                    depth = 0
                    in_string = False
                    escape_next = False
                    
                    for i, char in enumerate(brace_content):
                        if escape_next:
                            escape_next = False
                            continue
                        if char == '\\':
                            escape_next = True
                            continue
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        
                        if not in_string:
                            if char == '{':
                                depth += 1
                            elif char == '}':
                                depth -= 1
                                if depth == 0:
                                    potential_obj = brace_content[:i+1]
                                    try:
                                        obj = json.loads(potential_obj)
                                        logger.info("extracted_first_complete_object", title=obj.get('title', 'N/A'))
                                        return self._convert_to_issues([obj])
                                    except json.JSONDecodeError:
                                        pass
                                    break
        except Exception as e:
            logger.warning("truncated_json_extraction_failed", error=str(e))
        
        # 然后尝试查找JSON数组
        for match in re.finditer(r'\[[\s\S]*\]', response):
            potential = match.group()
            try:
                data = json.loads(potential)
                if isinstance(data, list) and len(data) > 0:
                    return self._convert_to_issues(data)
            except json.JSONDecodeError:
                continue

        # 策略3：查找JSON对象 {...}
        for match in re.finditer(r'\{[\s\S]*\}', response):
            potential = match.group()
            try:
                data = json.loads(potential)
                return self._parse_dict_response(data)
            except json.JSONDecodeError:
                continue

        # 如果不是 JSON，记录警告
        logger.warning("llm_response_not_json", response=response[:200])
        return []

    def _parse_dict_response(self, data: dict) -> list:
        """解析字典格式的响应"""
        # 处理单问题格式 (problem_exists: true)
        if "problem_exists" in data and data["problem_exists"]:
            issue = self._convert_single_problem_to_issue(data)
            if issue:
                return [issue]
        
        # 处理单问题格式 (直接有 issue/detail 字段)
        if "issue" in data and "detail" in data:
            issue = self._convert_issue_detail_to_issue(data)
            if issue:
                return [issue]
        
        # 处理问题描述类格式 (issue_type, problem_description, issue_description 等)
        if any(k in data for k in ["issue_type", "problem_description", "problem_detail", "issue_description"]):
            issue = self._convert_problem_desc_to_issue(data)
            if issue:
                return [issue]
        
        # 处理 issue + description 格式
        if "issue" in data and "description" in data:
            issue = self._convert_issue_desc_to_issue(data)
            if issue:
                return [issue]
        
        # 处理不同的字段名
        issues = None
        # 尝试多种可能的字段名
        for key in ["issues", "compliance_issues", "problems", "findings", "items", "results"]:
            if key in data:
                issues = data[key]
                break
        
        # 处理 review_dimensions 格式
        if "review_dimensions" in data:
            issues = self._convert_dimensions_to_issues(data["review_dimensions"])
            return issues
        
        # 处理 review_result 格式 (嵌套的审查结果)
        if "review_result" in data:
            review_result = data["review_result"]
            # 确保是字典类型
            if isinstance(review_result, dict):
                issues = self._convert_review_result_to_issues(review_result)
                return issues
        
        # 如果顶层有嵌套的issues
        if issues is None and "review_status" in data:
            issues = data.get("compliance_issues", [])
        
        if issues:
            logger.info("issues_found", issues_type=type(issues).__name__)
            if isinstance(issues, list):
                return self._convert_to_issues(issues)
            elif isinstance(issues, dict):
                return self._convert_to_issues([issues])
        
        return []

    def _convert_dimensions_to_issues(self, dimensions: list) -> list:
        """将审查维度转换为Issue对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel
        
        issues = []
        for dim in dimensions:
            # 跳过非字典项
            if not isinstance(dim, dict):
                logger.warning("skipping_non_dict_dimension", dim=str(dim)[:50])
                continue
            dimension_name = dim.get("dimension", "审查")
            dimension_issues = dim.get("issues", [])
            suggestions = dim.get("suggestions", [])
            status = dim.get("status", "")
            
            # 判断风险等级
            level = IssueLevel.MEDIUM
            if "缺失" in status or "无法" in status or "不合规" in status:
                level = IssueLevel.HIGH
            elif "待补充" in status or "不完整" in status:
                level = IssueLevel.MEDIUM
            elif "合规" in status or "符合" in status:
                level = IssueLevel.LOW
            
            for i, issue_text in enumerate(dimension_issues):
                issue = Issue(
                    issue_id=f"llm_{len(issues)}",
                    title=f"{dimension_name}问题",
                    description=issue_text,
                    level=level,
                    category=dimension_name,
                    location=IssueLocation(),
                    evidence=[IssueEvidence(
                        text=issue_text,
                        type="llm_analysis",
                        confidence=0.7,
                    )],
                    rule=IssueRule(
                        rule_id="LLM",
                        rule_name=f"LLM-{dimension_name}",
                        category=dimension_name,
                        severity=level.value,
                    ),
                    suggestion=IssueSuggestion(
                        type="modify",
                        original="",
                        suggested=suggestions[i] if i < len(suggestions) else "",
                        reason="",
                    ),
                    confidence=0.7,
                    source="llm",
                )
                issues.append(issue)
        
        return issues

    def _convert_review_result_to_issues(self, review_result: dict) -> list:
        """将review_result格式转换为Issue对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel
        
        issues = []
        
        for dimension_name, result in review_result.items():
            if not isinstance(result, dict):
                continue
            
            status = result.get("status", "")
            dimension_issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            
            # 判断风险等级
            level = IssueLevel.MEDIUM
            if "缺失" in status or "无法" in status or "不合规" in status:
                level = IssueLevel.HIGH
            elif "待补充" in status or "不完整" in status:
                level = IssueLevel.MEDIUM
            elif "合规" in status or "符合" in status:
                level = IssueLevel.LOW
            
            # 将维度名称转换为中文
            dimension_cn = {
                "non_discrimination_review": "非歧视性审查",
                "procurement_requirements_review": "采购需求审查",
                "scoring_standards_review": "评分标准审查",
                "qualification_requirements_review": "资质要求审查",
                "contract_terms_review": "合同条款审查",
            }.get(dimension_name, dimension_name.replace("_", " ").title())
            
            for i, issue_text in enumerate(dimension_issues):
                issue = Issue(
                    issue_id=f"llm_{len(issues)}",
                    title=f"{dimension_cn}问题",
                    description=issue_text,
                    level=level,
                    category=dimension_cn,
                    location=IssueLocation(),
                    evidence=[IssueEvidence(
                        text=issue_text,
                        type="llm_analysis",
                        confidence=0.7,
                    )],
                    rule=IssueRule(
                        rule_id="LLM",
                        rule_name=f"LLM-{dimension_cn}",
                        category=dimension_cn,
                        severity=level.value,
                    ),
                    suggestion=IssueSuggestion(
                        type="modify",
                        original="",
                        suggested=suggestions[i] if i < len(suggestions) else "",
                        reason="",
                    ),
                    confidence=0.7,
                    source="llm",
                )
                issues.append(issue)
        
        return issues

    def _convert_single_problem_to_issue(self, data: dict) -> Optional["Issue"]:
        """将单问题格式转换为Issue对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel
        
        # 提取问题字段
        title = data.get("problem_type", data.get("title", "发现问题"))
        description = data.get("problem_description", data.get("description", ""))
        category = data.get("category", data.get("problem_category", "合规审查"))
        risk = data.get("compliance_risk", data.get("risk", ""))
        recommendation = data.get("recommendation", data.get("suggestion", ""))
        legal_basis = data.get("legal_basis", data.get("legal_reference", ""))
        
        # 解析风险等级
        level_str = data.get("level", data.get("risk_level", data.get("severity", "medium")))
        if isinstance(level_str, str):
            level_lower = level_str.lower()
            if "high" in level_lower or "高" in level_str or "严重" in level_str:
                level = IssueLevel.HIGH
            elif "low" in level_lower or "低" in level_str or "轻微" in level_str:
                level = IssueLevel.LOW
            elif "info" in level_lower:
                level = IssueLevel.INFO
            else:
                level = IssueLevel.MEDIUM
        else:
            level = IssueLevel.MEDIUM
        
        issue = Issue(
            issue_id="llm_single",
            title=title,
            description=description,
            level=level,
            category=category,
            location=IssueLocation(),
            evidence=[IssueEvidence(
                text=description,
                type="llm_analysis",
                confidence=0.7,
            )],
            rule=IssueRule(
                rule_id="LLM",
                rule_name="LLM合规审查",
                category=category,
                severity=level.value,
            ),
                suggestion=IssueSuggestion(
                type="modify",
                original="",
                suggested=recommendation,
                reason=legal_basis,
            ),
            confidence=0.7,
            source="llm",
        )
        
        return issue

    def _convert_issue_desc_to_issue(self, data: dict) -> Optional["Issue"]:
        """将 issue + description 格式转换为Issue对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel
        
        title = data.get("issue", data.get("title", "发现问题"))
        description = data.get("description", "")
        category = data.get("category", data.get("type", "合规审查"))
        risk = data.get("risk", "")
        recommendation = data.get("suggestion", data.get("recommendation", ""))
        severity_str = data.get("severity", data.get("level", data.get("risk_level", "medium")))
        
        # 解析风险等级
        if isinstance(severity_str, str):
            if "高" in severity_str or "high" in severity_str.lower():
                level = IssueLevel.HIGH
            elif "低" in severity_str or "low" in severity_str.lower():
                level = IssueLevel.LOW
            elif "info" in severity_str.lower():
                level = IssueLevel.INFO
            else:
                level = IssueLevel.MEDIUM
        else:
            level = IssueLevel.MEDIUM
        
        issue = Issue(
            issue_id="llm_issue_desc",
            title=title,
            description=description,
            level=level,
            category=category,
            location=IssueLocation(),
            evidence=[IssueEvidence(
                text=description,
                type="llm_analysis",
                confidence=0.7,
            )],
            rule=IssueRule(
                rule_id="LLM",
                rule_name="LLM合规审查",
                category=category,
                severity=level.value,
            ),
            suggestion=IssueSuggestion(
                type="modify",
                original="",
                suggested=recommendation,
                reason=risk,
            ),
            confidence=0.7,
            source="llm",
        )
        
        return issue

    def _convert_issue_detail_to_issue(self, data: dict) -> Optional["Issue"]:
        """将 issue/detail 格式转换为Issue对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel
        
        title = data.get("issue", data.get("title", "发现问题"))
        description = data.get("detail", data.get("description", ""))
        category = data.get("category", data.get("type", "合规审查"))
        risk = data.get("risk", "")
        recommendation = data.get("suggestion", data.get("recommendation", ""))
        severity_str = data.get("severity", data.get("level", "medium"))
        
        # 解析风险等级
        if isinstance(severity_str, str):
            if "高" in severity_str or "high" in severity_str.lower():
                level = IssueLevel.HIGH
            elif "低" in severity_str or "low" in severity_str.lower():
                level = IssueLevel.LOW
            elif "info" in severity_str.lower():
                level = IssueLevel.INFO
            else:
                level = IssueLevel.MEDIUM
        else:
            level = IssueLevel.MEDIUM
        
        issue = Issue(
            issue_id="llm_issue",
            title=title,
            description=description,
            level=level,
            category=category,
            location=IssueLocation(),
            evidence=[IssueEvidence(
                text=description,
                type="llm_analysis",
                confidence=0.7,
            )],
            rule=IssueRule(
                rule_id="LLM",
                rule_name="LLM合规审查",
                category=category,
                severity=level.value,
            ),
            suggestion=IssueSuggestion(
                type="modify",
                original="",
                suggested=recommendation,
                reason=risk,
            ),
            confidence=0.7,
            source="llm",
        )
        
        return issue

    def _convert_problem_desc_to_issue(self, data: dict) -> Optional["Issue"]:
        """将问题描述类格式转换为Issue对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel
        
        title = data.get("issue_type", data.get("problem_type", data.get("title", "发现问题")))
        description = data.get("problem_description", data.get("problem_detail", data.get("description", data.get("issue_description", ""))))
        category = data.get("category", data.get("type", "合规审查"))
        risk = data.get("compliance_risk", data.get("potential_consequence", ""))
        recommendation = data.get("recommendation", data.get("suggestion", ""))
        severity_str = data.get("severity", data.get("level", data.get("risk", data.get("risk_level", data.get("compliance_risk", "medium")))))
        
        # 解析风险等级
        if isinstance(severity_str, str):
            if "高" in severity_str or "high" in severity_str.lower():
                level = IssueLevel.HIGH
            elif "低" in severity_str or "low" in severity_str.lower():
                level = IssueLevel.LOW
            elif "info" in severity_str.lower():
                level = IssueLevel.INFO
            else:
                level = IssueLevel.MEDIUM
        else:
            level = IssueLevel.MEDIUM
        
        issue = Issue(
            issue_id="llm_problem",
            title=title,
            description=description,
            level=level,
            category=category,
            location=IssueLocation(),
            evidence=[IssueEvidence(
                text=description,
                type="llm_analysis",
                confidence=0.7,
            )],
            rule=IssueRule(
                rule_id="LLM",
                rule_name="LLM合规审查",
                category=category,
                severity=level.value,
            ),
            suggestion=IssueSuggestion(
                type="modify",
                original="",
                suggested=recommendation,
                reason=risk,
            ),
            confidence=0.7,
            source="llm",
        )
        
        return issue

    def _convert_to_issues(self, items: list) -> list:
        """将字典转换为 Issue 对象"""
        from agent_recheck.models.issue import Issue, IssueEvidence, IssueLocation, IssueRule, IssueSuggestion, IssueLevel

        logger.info("converting_issues", items_type=type(items).__name__, items_len=len(items) if items else 0)
        
        issues = []
        for i, item in enumerate(items):
            try:
                # 跳过非字典类型的项（如整数、字符串等）
                if not isinstance(item, dict):
                    logger.warning("skipping_non_dict_item", index=i, item_type=type(item).__name__, item=str(item)[:50])
                    continue
                
                # 处理不同的字段名格式
                # 支持 dimension+issue 格式
                title = item.get("title", item.get("issue", item.get("description", "")[:50] or "发现问题"))
                # 支持 dimension+issue 格式，issue 作为描述
                description = item.get("description", item.get("issue", item.get("title", "")))
                category = item.get("category", item.get("dimension", item.get("type", "其他")))
                level_str = item.get("level", item.get("risk_level", item.get("severity", "medium")))
                quote = item.get("quote", item.get("evidence", item.get("text", "")))
                suggestion = item.get("suggestion", item.get("recommendation", item.get("整改建议", item.get("fix", ""))))
                reference = item.get("reference", item.get("legal_basis", item.get("法规依据", "")))
                confidence = item.get("confidence", item.get("certainty", 0.7))
                reason = item.get("reason", item.get("legal_basis", ""))

                # 解析level
                if isinstance(level_str, str):
                    level_map = {
                        "high": IssueLevel.HIGH, 
                        "medium": IssueLevel.MEDIUM, 
                        "low": IssueLevel.LOW, 
                        "info": IssueLevel.INFO,
                        "critical": IssueLevel.HIGH,
                    }
                    level = level_map.get(level_str.lower(), IssueLevel.MEDIUM)
                else:
                    level = level_str

                location = IssueLocation(
                    page=item.get("page", 0),
                    line=item.get("line", 0),
                    section=item.get("section", ""),
                    start=item.get("start", 0),
                    end=item.get("end", 0),
                    context=item.get("context", ""),
                )

                evidence = IssueEvidence(
                    text=quote,
                    type="matched",
                    confidence=confidence,
                )

                rule = IssueRule(
                    rule_id=item.get("rule_id", "LLM"),
                    rule_name=item.get("rule_name", "LLM识别"),
                    category=category,
                    severity=level_str if isinstance(level_str, str) else "medium",
                )

                suggestion_obj = IssueSuggestion(
                    type="modify",
                    original="",
                    suggested=suggestion,
                    reason=reason,
                )
                
                # 跳过占位符问题
                placeholder_titles = ("...", "N/A", "TBD", "", "问题描述", "标题", "无", "暂无", "未发现问题", "无问题", "未发现合规问题")
                placeholder_descs = ("...", "N/A", "TBD", "", "问题描述", "描述", "无", "暂无")
                if title in placeholder_titles or description in placeholder_descs:
                    logger.warning("skipping_placeholder_issue", title=title, description=description[:50] if description else "")
                    continue
                # 跳过标题和描述相同且为占位符的情况
                if title == description and (title in placeholder_titles or len(title) < 5):
                    logger.warning("skipping_duplicate_placeholder", title=title)
                    continue

                issue = Issue(
                    issue_id=f"llm_{len(issues)}",
                    title=title,
                    description=description,
                    level=level,
                    category=category,
                    location=location,
                    evidence=[evidence],
                    rule=rule,
                    suggestion=suggestion_obj,
                    confidence=confidence,
                    source="llm",
                )

                issues.append(issue)
            except Exception as e:
                logger.warning("issue_conversion_failed", error=str(e), item=str(item)[:100])

        return issues
