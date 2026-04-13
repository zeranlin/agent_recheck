"""一致性检查模块"""
# -*- coding: utf-8 -*-
"""
一致性检查模块

对解析后的内容进行一致性检查，包括：
1. 资质要求前后一致
2. 评分标准与分值匹配
3. 表格数据与文字描述一致
4. 时间节点逻辑正确
5. LLM 辅助一致性检查
"""

from typing import Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from ..parser.base import ParsedDocument
from ..parser.enhanced_table_parser import EnhancedTableParser, TableType
from ..engine.scoring_parser import ScoringParser
from ...utils.logging import get_logger

logger = get_logger("consistency")

# 导入 LLM 客户端
_llm_client = None


def get_llm_client():
    """获取 LLM 客户端（延迟加载）"""
    global _llm_client
    if _llm_client is None:
        from ..llm.client import LLMClient
        _llm_client = LLMClient.from_config_file()
    return _llm_client


class ConsistencyType(Enum):
    """一致性检查类型"""
    QUALIFICATION = "qualification"          # 资质要求一致
    SCORING = "scoring"                       # 评分标准一致
    TABLE_TEXT = "table_text"                # 表格与文字一致
    TIMELINE = "timeline"                    # 时间节点逻辑
    AMOUNT = "amount"                         # 金额数字一致
    NAME = "name"                             # 名称一致
    LLM_ANALYSIS = "llm_analysis"            # LLM 辅助分析


class Severity(Enum):
    """严重程度"""
    ERROR = "error"           # 错误，必须修复
    WARNING = "warning"       # 警告，建议检查
    INFO = "info"             # 信息，供参考


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    check_type: ConsistencyType
    severity: Severity
    title: str
    description: str
    location: dict = field(default_factory=dict)  # {section, page, line}
    evidence: list[str] = field(default_factory=list)
    suggestion: str = ""
    source: str = "rule"  # rule, llm


@dataclass
class ConsistencyResult:
    """一致性检查结果"""
    is_consistent: bool
    issues: list[ConsistencyIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)  # {severity: count}
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ConsistencyIssue) -> None:
        self.issues.append(issue)
        severity_key = issue.severity.value
        self.summary[severity_key] = self.summary.get(severity_key, 0) + 1
        if issue.severity == Severity.ERROR:
            self.is_consistent = False

    def get_issues_by_type(self, check_type: ConsistencyType) -> list[ConsistencyIssue]:
        return [i for i in self.issues if i.check_type == check_type]

    def get_issues_by_severity(self, severity: Severity) -> list[ConsistencyIssue]:
        return [i for i in self.issues if i.severity == severity]


class ConsistencyChecker:
    """一致性检查器"""

    def __init__(self, document: ParsedDocument, llm_enabled: bool = True):
        self.document = document
        self.table_parser = EnhancedTableParser()
        self.scoring_parser = ScoringParser()
        self.llm_enabled = llm_enabled
        self.result = ConsistencyResult(is_consistent=True)

    def check_all(self) -> ConsistencyResult:
        """执行所有一致性检查"""
        self._check_qualification_consistency()
        self._check_scoring_consistency()
        self._check_table_text_consistency()
        self._check_timeline_consistency()
        self._check_amount_consistency()
        self._check_name_consistency()
        
        # LLM 辅助一致性检查
        if self.llm_enabled:
            try:
                self._check_llm_consistency()
            except Exception as e:
                logger.warning("llm_consistency_check_failed", error=str(e))
        
        return self.result

    async def check_all_async(self) -> ConsistencyResult:
        """异步执行所有一致性检查"""
        self._check_qualification_consistency()
        self._check_scoring_consistency()
        self._check_table_text_consistency()
        self._check_timeline_consistency()
        self._check_amount_consistency()
        self._check_name_consistency()
        
        # LLM 辅助一致性检查
        if self.llm_enabled:
            await self._check_llm_consistency_async()
        
        return self.result

    def _check_qualification_consistency(self) -> None:
        """检查资质要求前后一致"""
        qualifications = []
        for section in self.document.sections:
            # 只处理有内容的章节
            text = section.content if hasattr(section, 'content') else ""
            if not text or len(text) < 50:
                continue
            
            if any(kw in text for kw in ["资质", "要求", "具备", "持有"]):
                qualifications.append({
                    "text": text,
                    "section": section.title if hasattr(section, 'title') else "",
                    "location": {"section": section.title if hasattr(section, 'title') else ""}
                })

        seen_qualifications = {}
        for qual in qualifications:
            for key_phrase in self._extract_key_phrases(qual["text"]):
                if key_phrase in seen_qualifications:
                    prev = seen_qualifications[key_phrase]
                    if not self._compare_qualification(qual, prev):
                        self.result.add_issue(ConsistencyIssue(
                            check_type=ConsistencyType.QUALIFICATION,
                            severity=Severity.WARNING,
                            title="资质要求不一致",
                            description=f"'{key_phrase}' 在不同位置的描述存在差异",
                            location=qual["location"],
                            evidence=[qual["text"][:200], prev["text"][:200]],
                            suggestion="确认资质要求是否为同一标准"
                        ))
                else:
                    seen_qualifications[key_phrase] = qual

    def _check_scoring_consistency(self) -> None:
        """检查评分标准与分值匹配"""
        scoring_tables = []
        for table in self.document.tables:
            # 处理 TableInfo dataclass 和 dict 两种情况
            table_type = getattr(table, 'type', '') or table.get("type", "") if isinstance(table, dict) else ""
            table_title = getattr(table, 'title', '') or table.get("title", "") if isinstance(table, dict) else ""
            
            if table_type == "scoring" or "评分" in table_title:
                scoring_tables.append(table)

        for table in scoring_tables:
            total_weight = 0
            rows = getattr(table, 'rows', []) or table.get("rows", []) if isinstance(table, dict) else []
            
            for row in rows:
                if isinstance(row, dict):
                    if row.get("is_header"):
                        continue
                    cells = row.get("cells", [{}])
                else:
                    cells = getattr(row, 'cells', [{}])
                
                if cells:
                    cell_text = cells[-1].get("text", "") if isinstance(cells[-1], dict) else getattr(cells[-1], 'text', "")
                else:
                    cell_text = ""
                
                weight = self._extract_number(cell_text)
                total_weight += weight

            if total_weight > 0 and abs(total_weight - 100) > 0.5:
                table_title = getattr(table, 'title', '') or table.get("title", "") if isinstance(table, dict) else ""
                self.result.add_issue(ConsistencyIssue(
                    check_type=ConsistencyType.SCORING,
                    severity=Severity.ERROR if abs(total_weight - 100) > 5 else Severity.WARNING,
                    title="评分权重不等于100%",
                    description=f"评分表中各项权重之和为 {total_weight}%，不等于100%",
                    location={"title": table_title},
                    evidence=[str(table_title), f"总和: {total_weight}%"],
                    suggestion="调整各评分项权重使其总和为100%"
                ))

    def _check_table_text_consistency(self) -> None:
        """检查表格数据与文字描述一致"""
        table_titles = set()
        for table in self.document.tables:
            # 处理 TableInfo dataclass 和 dict 两种情况
            if isinstance(table, dict):
                title = table.get("title", "")
            else:
                title = getattr(table, 'title', '') or ""
            if title:
                table_titles.add(title)

        for section in self.document.sections:
            # 使用 section.content 而不是 section.paragraphs
            text = section.content if hasattr(section, 'content') else ""
            if not text:
                continue
                
            for title in table_titles:
                if title in text and "见下表" in text:
                    related_tables = []
                    for t in self.document.tables:
                        if isinstance(t, dict):
                            t_title = t.get("title", "")
                        else:
                            t_title = getattr(t, 'title', '') or ""
                        if t_title == title:
                            related_tables.append(t)
                    
                    if not related_tables:
                        self.result.add_issue(ConsistencyIssue(
                            check_type=ConsistencyType.TABLE_TEXT,
                            severity=Severity.WARNING,
                            title="表格引用但未找到",
                            description=f"文档引用表格 '{title}'，但未找到该表格",
                            location={"section": section.title if hasattr(section, 'title') else ""},
                            evidence=[text[:200]],
                            suggestion="检查表格是否存在或编号是否正确"
                        ))

    def _check_timeline_consistency(self) -> None:
        """检查时间节点逻辑正确"""
        dates = []
        for section in self.document.sections:
            text = section.content if hasattr(section, 'content') else ""
            if not text:
                continue
            
            found_dates = self._extract_dates(text)
            for date in found_dates:
                dates.append({
                    "date": date,
                    "context": text[:100],
                    "section": section.title if hasattr(section, 'title') else ""
                })

        # 按日期排序（需要将日期字符串转为可比较格式）
        def date_sort_key(x):
            import re
            d = x["date"]
            match = re.search(r"(\d{4})[年/](\d{1,2})[月/](\d{1,2})", d)
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return (0, 0, 0)
        
        dates.sort(key=date_sort_key)

        for i in range(len(dates) - 1):
            current = dates[i]
            next_item = dates[i + 1]
            if "截止" in current["context"] or "截止" in next_item["context"]:
                if date_sort_key(current) > date_sort_key(next_item):
                    self.result.add_issue(ConsistencyIssue(
                        check_type=ConsistencyType.TIMELINE,
                        severity=Severity.ERROR,
                        title="时间逻辑错误",
                        description=f"存在后续日期早于截止日期的情况",
                        location={"section": current["section"]},
                        evidence=[current["context"], next_item["context"]],
                        suggestion="检查时间节点顺序是否合理"
                    ))

    def _check_amount_consistency(self) -> None:
        """检查金额数字一致"""
        amounts = {}
        for section in self.document.sections:
            text = section.content if hasattr(section, 'content') else ""
            if not text:
                continue
                
            found_amounts = self._extract_amounts(text)
            for amount, context in found_amounts:
                if amount in amounts:
                    if not self._compare_amount_context(amount, context, amounts[amount]["context"]):
                        self.result.add_issue(ConsistencyIssue(
                            check_type=ConsistencyType.AMOUNT,
                            severity=Severity.WARNING,
                            title="金额描述不一致",
                            description=f"金额 {amount} 在不同位置描述不一致",
                            evidence=[context[:100], amounts[amount]["context"][:100]],
                            suggestion="确认金额是否为同一笔款项"
                        ))
                else:
                    amounts[amount] = {"context": context, "section": section.title if hasattr(section, 'title') else ""}

    def _check_name_consistency(self) -> None:
        """检查名称一致"""
        names = {}
        for section in self.document.sections:
            text = section.content if hasattr(section, 'content') else ""
            if not text:
                continue
                
            found_names = self._extract_project_names(text)
            for name in found_names:
                if name in names:
                    if not self._fuzzy_match(name, names[name]):
                        self.result.add_issue(ConsistencyIssue(
                            check_type=ConsistencyType.NAME,
                            severity=Severity.INFO,
                            title="项目名称可能不一致",
                            description=f"项目名称可能有多种写法",
                            evidence=[name, names[name]],
                            suggestion="统一项目名称写法"
                        ))
                else:
                    names[name] = name

    def _extract_key_phrases(self, text: str) -> list[str]:
        """提取关键短语"""
        import re
        patterns = [
            r"(ISO\d+[^\s，,。]+)",
            r"([一二三甲乙丙级]+资质)",
            r"(供应商|投标人|承包商)[^\s，,。]+",
        ]
        phrases = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phrases.extend(matches)
        return phrases

    def _compare_qualification(self, q1: dict, q2: dict) -> bool:
        """比较两个资质要求是否一致"""
        text1 = q1["text"].lower()
        text2 = q2["text"].lower()
        similarity = self._calculate_similarity(text1, text2)
        return similarity > 0.8

    def _compare_amount_context(self, amount: str, context1: str, context2: str) -> bool:
        """比较两个金额上下文是否一致"""
        # 检查上下文是否包含相同的描述
        # 简单检查：如果两个上下文都提到相同的金额类型，则认为一致
        return context1 == context2

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算文本相似度"""
        set1 = set(s1)
        set2 = set(s2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _fuzzy_match(self, s1: str, s2: str) -> bool:
        """模糊匹配"""
        import re
        clean1 = re.sub(r"[^\w]", "", s1.lower())
        clean2 = re.sub(r"[^\w]", "", s2.lower())
        return clean1 in clean2 or clean2 in clean1

    def _extract_number(self, text: str) -> float:
        """提取数字"""
        import re
        match = re.search(r"[\d.]+", text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return 0.0
        return 0.0

    def _extract_dates(self, text: str) -> list[str]:
        """提取日期"""
        import re
        patterns = [
            r"\d{4}年\d{1,2}月\d{1,2}日",
            r"\d{4}-\d{2}-\d{2}",
            r"\d{4}/\d{2}/\d{2}",
        ]
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        return dates

    def _extract_amounts(self, text: str) -> list[tuple[str, str]]:
        """提取金额"""
        import re
        pattern = r"(?:人民币|元|RMB|USD|\$)?\s*[\d,]+(?:\.\d{1,2})?\s*(?:万元|万|元|美元|USD)?"
        matches = re.findall(pattern, text)
        return [(m, text) for m in matches]

    def _extract_project_names(self, text: str) -> list[str]:
        """提取项目名称"""
        import re
        pattern = r"《([^》]+)》|([^\s，,。]{5,20}项目)"
        matches = re.findall(pattern, text)
        return [m[0] or m[1] for m in matches if m[0] or m[1]]

    def _check_llm_consistency(self) -> None:
        """使用 LLM 进行一致性检查（同步包装）"""
        try:
            # 直接创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._check_llm_consistency_async())
            finally:
                loop.close()
        except Exception as e:
            logger.warning("llm_consistency_check_error", error=str(e))

    async def _check_llm_consistency_async(self) -> None:
        """使用 LLM 进行一致性检查（异步）"""
        try:
            client = get_llm_client()
            if not await client.is_available():
                logger.warning("llm_not_available_for_consistency")
                return

            # 构建一致性检查提示词
            prompt = self._build_consistency_prompt()
            
            # 使用 _call_with_retry 获取解析后的 JSON 结果
            result_text = await client._call_with_retry(prompt)
            
            if result_text:
                self._parse_llm_consistency_result(result_text)
            
        except Exception as e:
            logger.warning("llm_consistency_check_failed", error=str(e))

    def _build_consistency_prompt(self) -> str:
        """构建一致性检查提示词"""
        # 收集关键信息
        sections_text = []
        for section in self.document.sections[:20]:  # 限制数量
            section_content = section.content if hasattr(section, 'content') else getattr(section, 'text', '')
            if not section_content:
                continue
            section_title = section.title if hasattr(section, 'title') else ''
            sections_text.append(f"【{section_title}】\n{section_content[:500]}")
        
        tables_text = []
        for i, table in enumerate(self.document.tables[:10]):
            if isinstance(table, dict):
                table_title = table.get('title', '') or ''
                table_content = table.get('content', '') or ''
            else:
                table_title = getattr(table, 'title', '') or ''
                table_content = getattr(table, 'content', '') or ''
            if table_content:
                tables_text.append(f"【表格{i+1}】{table_title}\n{table_content[:300]}")
        
        prompt = f"""请分析以下招投标文件，找出可能存在的一致性问题。请直接输出JSON格式结果，不要输出任何思考过程。

## 文档段落：
{chr(10).join(sections_text)}

## 表格：
{chr(10).join(tables_text)}

请重点检查以下类型的一致性问题：
1. 资质要求前后矛盾（如前面要求ISO认证，后面又说可选）
2. 评分标准分值不匹配（如说满分100分但各项加起来超过100）
3. 时间节点逻辑错误（如截止日期早于开始日期）
4. 金额数字不一致（如大写金额与小写金额不符）
5. 表格与文字描述矛盾（如说"见下表"但表格不存在）

直接输出JSON格式：
{{
  "issues": [
    {{
      "type": "qualification|scoring|timeline|amount|table_text",
      "severity": "error|warning|info",
      "title": "问题标题",
      "description": "详细描述",
      "location": {{"section": "相关章节"}},
      "evidence": ["证据1", "证据2"],
      "suggestion": "修改建议"
    }}
  ]
}}
如果没有问题，返回空的issues数组。"""
        return prompt

    def _parse_llm_consistency_result(self, result_text: str) -> None:
        """解析 LLM 返回的一致性检查结果"""
        import json
        import re
        
        if not result_text:
            logger.warning("llm_consistency_empty_response")
            return
        
        try:
            # 对于 qwen3 的 reasoning 格式，需要提取最后的 JSON 部分
            # 通常 JSON 在 ```json ... ``` 代码块中，或在文档末尾
            
            # 方法1: 尝试提取 ```json 或 ``` 代码块中的内容
            json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', result_text)
            if json_block_match:
                json_text = json_block_match.group(1).strip()
            else:
                # 方法2: 对于思考过程格式，尝试提取最后的JSON部分
                # 通常在 "Final Answer:", "结论:", "JSON Output:" 等标记后
                final_match = re.search(r'(?:Final Answer|结论|JSON Output|最终输出)[\s:]*([\s\S]*)$', result_text)
                if final_match:
                    json_text = final_match.group(1).strip()
                    # 尝试从结果中提取JSON
                    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', json_text)
                    if json_match:
                        json_text = json_match.group(1)
                    else:
                        json_text = json_text[:2000]  # 取最后2000字符作为JSON尝试
                else:
                    # 方法3: 直接搜索 JSON 对象或数组
                    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', result_text)
                    if json_match:
                        json_text = json_match.group(1)
                    else:
                        # 方法4: 尝试将思考过程后的大部分内容作为JSON解析
                        # 寻找可能的JSON开始位置
                        json_start = result_text.rfind('{')
                        if json_start > len(result_text) // 2:  # JSON在文本后半部分
                            json_text = result_text[json_start:]
                        else:
                            logger.warning("llm_consistency_response_not_json", preview=result_text[:200])
                            return
            
            data = json.loads(json_text)
            
            # 兼容多种 JSON 格式
            # 格式1: {"issues": [...]} - 标准格式
            # 格式2: {"analysis_result": [...]} - qwen 返回格式
            # 格式3: {"consistency_issues": [...]} - qwen 一致性检查格式
            # 格式4: 直接是数组 [...]
            if isinstance(data, dict):
                issues_list = data.get("issues", data.get("analysis_result", data.get("consistency_issues", [])))
            elif isinstance(data, list):
                issues_list = data
            else:
                issues_list = []
            
            for item in issues_list:
                try:
                    # 兼容不同字段名
                    check_type_str = item.get("type", item.get("issue_type", "llm_analysis"))
                    try:
                        check_type = ConsistencyType(check_type_str)
                    except ValueError:
                        check_type = ConsistencyType.LLM_ANALYSIS
                    
                    # 兼容 severity/risk_level 字段
                    severity_str = item.get("severity", item.get("risk_level", "warning"))
                    severity_map = {"高": "error", "中": "warning", "低": "info", 
                                   "high": "error", "medium": "warning", "low": "info"}
                    severity_str = severity_map.get(severity_str, severity_str)
                    try:
                        severity = Severity(severity_str)
                    except ValueError:
                        severity = Severity.WARNING
                    
                    issue = ConsistencyIssue(
                        check_type=check_type,
                        severity=severity,
                        title=item.get("title", item.get("description", "一致性问题")),
                        description=item.get("description", item.get("reason", "")),
                        location={"section": item.get("segment", "")},
                        evidence=[item.get("reason", ""), item.get("description", "")],
                        suggestion=item.get("suggestion", ""),
                        source="llm",
                    )
                    self.result.add_issue(issue)
                except Exception as e:
                    logger.warning("llm_issue_parse_error", error=str(e))
                    
        except json.JSONDecodeError as e:
            logger.warning("llm_consistency_json_decode_error", error=str(e))
