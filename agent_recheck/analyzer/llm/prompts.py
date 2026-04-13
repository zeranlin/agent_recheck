# -*- coding: utf-8 -*-
"""
LLM 提示词模板

包含各类分析任务的提示词模板：
- 合规性审查
- 条款分类
- 风险评估
- 建议生成
"""

from typing import Optional, Dict, Any


class PromptTemplates:
    """提示词模板管理"""
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业的政府采购招投标文件合规审查专家。

你的职责是：
1. 识别招投标文件中的违规风险点
2. 引用相关法规条款
3. 提供修改建议

审查范围：
- 非歧视性原则（不得对供应商实行差别待遇）
- 采购需求的合理性
- 评分标准的公平性
- 合同条款的完整性
- 资质要求的适当性

请严格依据以下法规进行审查：
- 《政府采购法》及其实施条例
- 《招标投标法》及其实施条例
- 《政府采购货物和服务招标投标管理办法》（87号令）
- 《政府采购需求管理办法》
- 地方性法规（如《深圳经济特区政府采购条例》）

重要要求：
1. 直接输出JSON数组格式，不要输出任何其他文字
2. 每个问题必须包含具体的标题、描述、风险等级和整改建议
3. 描述中要包含从文档中找到的具体内容，不能使用省略号
4. 最多返回5个最严重的问题
5. 如果文档没有问题或无法分析，返回空数组 []"""

    @classmethod
    def get_analysis_prompt(cls) -> str:
        """获取文档分析提示词"""
        return """你是政府采购合规审查专家。请分析以下招标文件，识别所有违规问题。

文件：{document_title}
内容：
{document_content}

【必须检查的问题类型】

1. **非歧视性**：
   - 地域限制（如"深圳市本地业绩"）
   - 外地供应商参与障碍
   - 所有制歧视

2. **采购需求**：
   - 品牌倾向（如"等同于XX品牌"）
   - 占位符未填写
   - 关键参数缺失
   - 认证证书要求（如ISO9001、ISO14001等）

3. **价格评分**：
   - 价格分权重超过60%
   - 中小企业价格扣除政策缺失
   - 评分标准未量化

4. **资质要求**：
   - 业绩要求过高
   - 注册资本门槛过高
   - 认证证书超出必要范围

5. **合同条款**：
   - 履约保证金超过10%
   - 违约金比例过高
   - 预付款比例超过30%

6. **中小企业**：
   - 未规定中小企业价格扣除比例

7. **完整性检查**：
   - 联系方式缺失（联系人、电话、邮箱等）

【输出要求】
- 报告所有发现的问题，不要遗漏
- 每个问题必须有文档原文作为依据
- 最多返回8个问题
- 没有问题返回空数组[]

输出JSON数组，每个问题包含：
{{"title": "具体问题", "description": "文档原文（完整句子）", "level": "high/medium/low", "category": "类别", "suggestion": "整改建议"}}

注意：
- 必须返回JSON数组，不要返回任何其他格式
- 每个问题都要有完整的description，包含原文
- 如果没有问题，返回空数组[]"""

    @classmethod
    def get_table_analysis_prompt(cls) -> str:
        """获取表格分析提示词"""
        return """请分析以下表格内容，识别可能存在的合规性问题：

表格标题：{table_title}
表格内容：
{table_content}

表格类型可能是：
- 评分标准表
- 技术参数表
- 资质要求表
- 合同条款表
- 实质性条款表

请识别：
1. 表格中标记为 ★ 或 ■ 的实质性条款
2. 表格中的评分因素和分值是否合理
3. 表格中是否存在歧视性要求
4. 表格内容与其他章节的一致性

输出 JSON 格式的问题列表。"""

    @classmethod
    def get_scoring_analysis_prompt(cls) -> str:
        """获取评分标准分析提示词"""
        return """请分析以下评分标准，识别可能存在的问题：

评分标准内容：
{scoring_content}

请检查：
1. **价格分权重**：是否在合理范围内（10%-70%）？
2. **主观分比例**：技术分、商务分是否过高（>50%）？
3. **评分因素**：是否细化量化？有无明确的评分标准？
4. **实质性要求**：是否明确标注？
5. **公平性**：是否存在对特定供应商有利的条款？

输出 JSON 格式的问题列表。"""

    @classmethod
    def get_classification_prompt(cls) -> str:
        """获取条款分类提示词"""
        return """请将以下条款分类到相应的类别：

条款内容：
{clause_content}

可选类别：
- discrimination: 非歧视性问题
- scoring: 评分标准问题
- qualification: 资质要求问题
- procurement: 采购需求问题
- contract: 合同条款问题
- certification: 认证证书问题
- other: 其他问题

输出格式：
{{
  "category": "分类名称",
  "reason": "分类理由",
  "keywords": ["关键词1", "关键词2"]
}}"""

    @classmethod
    def get_risk_assessment_prompt(cls) -> str:
        """获取风险评估提示词"""
        return """请评估以下风险点的严重程度：

风险内容：
{risk_content}

风险类型：{risk_type}

请评估：
1. **严重程度**：high（高）/ medium（中）/ low（低）
2. **影响范围**：该问题会影响哪些供应商？
3. **法规依据**：违反哪条法规？
4. **整改建议**：如何修改以符合要求？

输出格式：
{{
  "level": "high/medium/low",
  "impact": "影响范围说明",
  "reference": "法规依据",
  "suggestion": "整改建议",
  "confidence": 0.0-1.0
}}"""

    @classmethod
    def get_summary_prompt(cls) -> str:
        """获取报告摘要提示词"""
        return """请为以下审查结果生成摘要：

审查结果：
{results}

摘要应包含：
1. 总体评价（合格/基本合格/不合格）
2. 问题数量统计（按级别）
3. 主要问题列表
4. 改进建议

输出格式：
{{
  "overall": "合格/基本合格/不合格",
  "total_issues": 总数,
  "high_risk": 高风险数,
  "medium_risk": 中风险数,
  "low_risk": 低风险数,
  "summary": "总体评价说明",
  "main_issues": ["主要问题1", "主要问题2"],
  "recommendations": ["建议1", "建议2"]
}}"""


class StructuredOutputParser:
    """结构化输出解析器"""
    
    # 支持的输出模式
    MODES = {
        "issues": "Issue列表",
        "classification": "分类结果",
        "risk_assessment": "风险评估",
        "summary": "摘要",
        "scoring_analysis": "评分分析",
    }
    
    @classmethod
    def parse(cls, response: str, mode: str = "issues") -> Dict[str, Any]:
        """
        解析 LLM 响应
        
        Args:
            response: LLM 响应文本
            mode: 解析模式
            
        Returns:
            解析后的结构化数据
        """
        import json
        import re
        
        # 尝试提取 JSON
        json_match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", response)
        if not json_match:
            return {"error": "无法解析响应", "raw": response}
        
        try:
            data = json.loads(json_match.group())
            return cls._validate_and_convert(data, mode)
        except json.JSONDecodeError as e:
            return {"error": f"JSON解析失败: {e}", "raw": response}
    
    @classmethod
    def _validate_and_convert(cls, data: Any, mode: str) -> Dict[str, Any]:
        """验证和转换数据"""
        if mode == "issues":
            return cls._convert_issues(data)
        elif mode == "classification":
            return cls._convert_classification(data)
        elif mode == "risk_assessment":
            return cls._convert_risk(data)
        elif mode == "summary":
            return cls._convert_summary(data)
        else:
            return {"data": data}
    
    @classmethod
    def _convert_issues(cls, data: Any) -> Dict[str, Any]:
        """转换问题列表"""
        if isinstance(data, dict) and "issues" in data:
            issues = data["issues"]
        elif isinstance(data, list):
            issues = data
        else:
            return {"error": "无效的问题格式", "data": data}
        
        return {"issues": issues, "count": len(issues)}
    
    @classmethod
    def _convert_classification(cls, data: Any) -> Dict[str, Any]:
        """转换分类结果"""
        if isinstance(data, dict):
            return data
        return {"error": "无效的分类格式", "data": data}
    
    @classmethod
    def _convert_risk(cls, data: Any) -> Dict[str, Any]:
        """转换风险评估"""
        if isinstance(data, dict):
            return data
        return {"error": "无效的风险格式", "data": data}
    
    @classmethod
    def _convert_summary(cls, data: Any) -> Dict[str, Any]:
        """转换摘要"""
        if isinstance(data, dict):
            return data
        return {"error": "无效的摘要格式", "data": data}


# 导出
__all__ = [
    'PromptTemplates',
    'StructuredOutputParser',
]
