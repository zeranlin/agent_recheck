"""Prompt 模板"""

from string import Template


class PromptTemplates:
    """Prompt 模板集合"""

    @staticmethod
    def get_analysis_prompt() -> str:
        """获取分析提示词模板"""
        return Template("""你是专业的政府采购招投标文件合规审查专家。

请审查以下招标文件，识别其中的合法合规性风险点。

## 文件信息
文件名：${document_title}

## 招标文件内容
${document_content}

## 审查要求

请从以下维度进行审查：

1. **非歧视性**：是否有限制特定区域、行业、品牌的要求
2. **采购需求合理性**：技术要求是否合理，是否指向特定供应商
3. **评分标准合规性**：评分标准是否量化，主观分占比是否过高
4. **合同条款风险**：付款条件、违约金、履约保证金是否合理
5. **政策落实**：是否落实中小企业预留等政策

## 输出格式

请以 JSON 格式输出结果：
```json
[
  {
    "category": "风险类别",
    "level": "high/medium/low",
    "title": "问题标题",
    "quote": "原文引用",
    "line": 行号,
    "reference": "法规依据",
    "suggestion": "修改建议",
    "confidence": 置信度(0-1)
  }
]
```

如果未发现问题，请返回空数组 `[]`。
""")

    @staticmethod
    def get_consistency_check_prompt() -> str:
        """获取一致性检查提示词模板"""
        return Template("""你是政府采购领域专家。

请检查以下招标文件中的前后一致性：

${document_content}

## 检查要点

1. 采购标的与评分标准是否一致
2. 技术要求与合同条款是否矛盾
3. 引用的法规是否有效
4. 章节编号是否连续

请以 JSON 格式输出发现的不一致问题：
```json
[
  {
    "type": "不一致类型",
    "location1": "位置1",
    "location2": "位置2",
    "description": "描述"
  }
]
```
""")

    @staticmethod
    def get_risk_assessment_prompt() -> str:
        """获取风险评估提示词模板"""
        return """请评估以下问题的风险等级和修改优先级：

问题描述：{problem}
原文引用：{quote}
相关法规：{reference}

评估维度：
1. 法律风险：是否违反法律法规
2. 投诉风险：供应商投诉可能性
3. 审计风险：被审计发现的概率
4. 整改成本：修改的难度

输出：
{
  "risk_level": "high/medium/low",
  "priority": "urgent/normal/low",
  "reasoning": "评估理由"
}
"""
