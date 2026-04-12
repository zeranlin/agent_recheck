# 政府采购招投标文件合规性审查智能体设计文档

**版本**：v1.3
**日期**：2026-04-12
**状态**：草稿

---

## 1. 项目概述

### 1.1 目标
构建一个政府采购招投标文件合规性审查智能体，能够自动识别招标文件中的合法合规性风险点，并提供详细的证据定位和改进建议。

### 1.2 使用场景
- 运行在隔离的内网环境中
- 使用自有 LLM（qwen3.5-27b）
- 可提供约 100 份样本文件用于规则训练
- CLI 工具形态，无需图形界面

### 1.3 核心价值
- 精准定位风险点
- 提供充分证据和法规依据
- 支持规则自学习和迭代优化
- 高可用、高可靠的审查能力

---

## 2. 系统架构

### 2.1 整体架构

```
agent_recheck/
├── cli/                      # 命令行入口
├── analyzer/                 # 分析引擎
│   ├── parser/              # 文档解析
│   ├── engine/              # 规则引擎
│   ├── llm/                 # LLM 调用
│   ├── aggregator/          # 结果聚合
│   └── report/              # 报告生成
├── config/                   # 配置文件
├── knowledge/                # 离线知识库
│   ├── regulations/          # 法规原文
│   └── sync/                # 同步工具
├── models/                   # 数据模型
├── utils/                    # 工具函数
├── tracker/                  # 监控埋点
├── evaluator/                # 准确性评估
└── tests/                    # 测试套件
```

### 2.2 三层审查体系

```
┌─────────────────────────────────────────────────────────┐
│                    第一层：规则引擎                      │
│  ├── 格式完整性检查                                      │
│  ├── 硬性合规检测（明确违法条款）                         │
│  └── 结构化提取（预算金额、评标方法等字段）                 │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   第二层：AI 深度分析                     │
│  ├── 语义理解审查（隐性歧视、变相排斥）                   │
│  ├── 上下文一致性检查（前后矛盾）                         │
│  ├── 跨段落一致性审查                                    │
│  ├── 风险分级评估                                        │
│  └── 改进建议生成                                        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  第三层：规则校验 + 输出                   │
│  ├── AI 审查结果交叉验证                                 │
│  ├── 风险点聚合去重                                      │
│  └── 结构化报告生成                                      │
└─────────────────────────────────────────────────────────┘
```

### 2.3 混合分析引擎（容错设计）

```python
# analyzer/engine/hybrid_engine.py

class HybridAnalysisEngine:
    """混合分析引擎，支持降级"""
    
    async def analyze(self, document, context):
        # 优先使用混合模式
        try:
            if await self.llm.is_available(timeout=5):
                return await self.analyze_with_hybrid(document, context)
            else:
                # LLM 不可用，降级到纯规则模式
                logger.warning("LLM unavailable, falling back to rules only")
                return await self.analyze_with_rules_only(document, context)
        except LLMTimeoutError:
            logger.error("LLM timeout, falling back to rules only")
            return await self.analyze_with_rules_only(document, context)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
```

### 2.4 文档内容分层

```
┌─────────────────────────────────────────────────────────┐
│                   招标文件内容分层                        │
├─────────────────────────────────────────────────────────┤
│  1. 模板套语层（不审查）                                 │
│     - 固定模板库匹配                                     │
│     - 识别方式：重复出现段落                             │
│                                                             │
│  2. 格式说明层（轻审查）                                 │
│     - 封面格式、装订顺序等                               │
│     - 识别方式：章节标题含"格式""说明"                    │
│                                                             │
│  3. 实质性内容层（重点审查）                             │
│     - 供应商资格条件                                    │
│     - 采购需求/技术规格                                  │
│     - 评分标准                                          │
│     - 合同条款                                          │
│     - 业绩要求                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 审查范围

### 3.1 文件完整性审查
根据 87 号令第二十条，招标文件应当包含：
- 投标邀请、投标人须知
- 投标人资格条件证明文件
- 采购需求（技术规格、数量、服务标准）
- 投标报价要求和投标保证金
- 评标方法、评标标准和无效情形
- 合同文本、履约验收要求
- 采购资金支付方式
- 其他法定事项

### 3.2 合规性审查

#### 非歧视性审查
| 编号 | 场景 | 风险等级 | 法规依据 |
|------|------|----------|----------|
| 1 | 限定特定区域业绩 | 高 | 实施条例第20条第4款 |
| 2 | 限定特定行业业绩 | 高 | 实施条例第20条第4款 |
| 3 | 指定品牌/专利 | 高 | 实施条例第20条第6款 |
| 4 | 规模条件作为评分项 | 高 | 87号令第55条第4款 |
| 5 | 技术指向特定供应商 | 高 | 需求管理办法第10条 |
| 6 | 资质证书指向特定机构 | 高 | 不得限定特定机构 |
| 7 | 售后服务地域限定 | 高 | 不得限定特定区域 |
| 8 | 特定所有制形式暗示 | 中 | 政府采购法第9条 |
| 9 | 本地化壁垒（服务网点） | 高 | 实施条例第20条第7款 |
| 10 | 人员户籍限定 | 中 | 实施条例第7条 |
| 11 | 关联企业限制 | 中 | 公平竞争原则 |
| 12 | 社保缴纳地限定 | 高 | 不得限定特定区域 |

#### 采购需求合规性
| 编号 | 场景 | 风险等级 | 法规依据 |
|------|------|----------|----------|
| 13 | 技术要求指向特定供应商 | 高 | 需求管理办法第10条 |
| 14 | 功能要求指向特定产品 | 高 | 需求管理办法第10条 |
| 15 | 规格参数超标准要求 | 高 | 需求管理办法第10条 |
| 16 | 环保要求与产品类型不匹配 | 中 | 绿色采购暂行办法 |
| 17 | 兼容性问题实质指向 | 高 | 不得设置无关条件 |
| 18 | 检测报告特定化 | 中 | 应明确资质范围 |
| 19 | 验收标准缺失或模糊 | 高 | 87号令第20条第7款 |
| 20 | 检测报告有效性未明确 | 中 | 明确证书有效期 |

#### 评分标准合规性
| 编号 | 场景 | 风险等级 | 法规依据 |
|------|------|----------|----------|
| 21 | 评分标准未量化 | 高 | 87号令第55条 |
| 22 | 主观分占比过高 | 高 | 87号令第55条 |
| 23 | 价格分权重失衡 | 中 | 一般货物价格分≥60% |
| 24 | 报价合理性审查缺失 | 中 | 应有成本审查 |
| 25 | 中小企业价格扣除叠加 | 中 | 价格扣除上限 |

#### 合同条款风险
| 编号 | 场景 | 风险等级 | 参考依据 |
|------|------|----------|----------|
| 26 | 付款条件不公平（360日） | 高 | 行业惯例≤90日 |
| 27 | 履约保证金过高（>10%） | 高 | 合理范围≤10% |
| 28 | 知识产权归属不公 | 中 | 民法典 |
| 29 | 违约金比例过高（>3‰/日） | 高 | 民法典第585条 |
| 30 | 合同变更无限制 | 高 | 变更上限15% |
| 31 | 验收程序复杂化 | 中 | 合理流程 |
| 32 | 争议解决地点偏向 | 中 | 公平原则 |
| 33 | 不可抗力定义过窄 | 中 | 现代不可抗力 |

### 3.3 一致性审查

| 编号 | 场景 | 风险等级 | 法规依据 |
|------|------|----------|----------|
| 34 | 采购标的与标准矛盾 | 高 | 需求合理性 |
| 35 | 引用失效法规 | 高 | 需核实有效性 |
| 36 | 禁止进口与国标矛盾 | 高 | 政府采购法 |
| 37 | 前后描述不一致 | 高 | 文件一致性 |

### 3.4 政策落实审查

| 编号 | 场景 | 风险等级 | 法规依据 |
|------|------|----------|----------|
| 38 | 中小企业预留缺失 | 中 | 财库〔2020〕46号 |
| 39 | 节能采购未执行 | 中 | 节能产品采购意见 |
| 40 | 进口产品审核缺失 | 中 | 进口论证要求 |

---

## 4. 规则引擎设计

### 4.1 规则结构

```yaml
rules:
  - id: DIS-001
    name: 禁止限定特定行政区域业绩
    category: 非歧视性
    level: high
    severity: critical
    
    pattern:
      type: regex
      match: 
        - "(北京|上海|广东|四川|浙江)..{0,10}业绩"
        - ".{0,5}省.{0,10}业绩"
      exclude_context:
        - "全国"
        - "不限"
    
    verification:
      check_type: negative
    
    reference:
      law: "政府采购法实施条例"
      article: "第二十条第四款"
      
    suggestion:
      template: "修改为'投标截止前{years}年内完成的政府采购业绩'"
```

### 4.2 规则数量分级处理

| 规则数量 | 处理策略 |
|----------|----------|
| 1-50条 | 全量匹配 |
| 50-200条 | 按类别匹配 + 缓存 |
| 200-500条 | 索引优化 + 类别过滤 |
| 500+条 | 分层索引 + LLM 预筛选 |

### 4.3 规则自学习流程

```
LLM 审查结果
    │
    ▼
规则提取器（识别可模式化内容）
    │
    ▼
候选规则生成（正则/关键词）
    │
    ├── 置信度 ≥ 0.8 → 进入审核队列
    └── 置信度 < 0.8 → 人工创建
            │
            ▼
    ┌──────────────────┐
    │  规则审核工作流   │
    │  - 业务专家审核   │
    │  - 小范围验证     │
    │  - 灰度发布       │
    └──────────────────┘
            │
            ▼
    ┌──────────────────┐
    │  规则版本管理     │
    │  - 版本记录       │
    │  - 一键回滚       │
    │  - 冲突检测       │
    └──────────────────┘
            │
            ▼
      规则库注册
```

### 4.4 规则质量把控

```python
# analyzer/engine/rule_manager.py

class RuleManager:
    """规则生命周期管理"""
    
    def register_rule(self, rule: Rule, approval: bool = False):
        """
        注册规则：
        1. 验证规则格式
        2. 冲突检测
        3. 测试集验证
        4. 人工审批（可选）
        5. 灰度发布（可选）
        """
        
    def deprecate_rule(self, rule_id: str, reason: str):
        """废弃规则，保留历史记录"""
        
    def rollback_rule(self, rule_id: str, version: str):
        """回滚到指定版本"""
        
    def check_conflicts(self, rule: Rule) -> List[Conflict]:
        """检测规则冲突"""
```

---

## 5. LLM 审查设计

### 5.1 System Prompt 要点

```
你是一个专业的政府采购招投标文件合规审查专家。

审查维度：
1. 非歧视性
2. 采购需求合理性
3. 评分标准合规性
4. 前后一致性
5. 履约风险

输出：JSON格式，包含问题、证据、定位、法规依据、置信度、修改建议
```

### 5.2 跨段落审查

```python
# analyzer/llm/consistency_checker.py

class ConsistencyChecker:
    """跨段落一致性检查"""
    
    def check(self, document):
        checks = [
            self.check_procurement_type_consistency,  # 采购类型一致性
            self.check_regulation_validity,           # 法规有效性
            self.check_standard_consistency,          # 标准一致性
        ]
```

### 5.3 分段审查策略

```
文档 → 智能分段（按章节，~2000字/段）→ 并行 LLM 审查 → 结果聚合
```

### 5.4 LLM 调用保护机制

```python
# analyzer/llm/client.py

class LLMClient:
    """LLM 调用封装，含容错保护"""
    
    def __init__(self, config: LLMConfig):
        self.timeout = config.timeout or 30
        self.max_retries = config.max_retries or 3
        self.fallback_enabled = config.fallback_enabled
    
    async def analyze(self, text: str, context: dict) -> AnalysisResult:
        try:
            return await self._call_with_retry(text, context)
        except TimeoutError:
            logger.warning("LLM call timeout")
            raise LLMTimeoutError("LLM 分析超时")
        except LLMServiceError as e:
            logger.error(f"LLM service error: {e}")
            raise LLMUnavailableError("LLM 服务不可用")
    
    async def is_available(self, timeout: float = 5) -> bool:
        """检查 LLM 服务是否可用"""
        try:
            await asyncio.wait_for(self.client.ping(), timeout=timeout)
            return True
        except:
            return False
```

### 5.5 Token 消耗监控

```python
# tracker/token_tracker.py

class TokenTracker:
    """Token 消耗追踪"""
    
    def track(self, operation: str, tokens: int):
        """
        记录 Token 消耗
        - operation: analyze / learn / consistency_check
        - tokens: 消耗数量
        """
        
    def get_consumption_report(self) -> ConsumptionReport:
        """生成消耗报告"""
        
    def check_quota(self) -> bool:
        """检查是否超配额"""
```

---

## 6. 准确性评估框架

### 6.1 评估指标

```python
# evaluator/accuracy_evaluator.py

class AccuracyEvaluator:
    """审查准确性评估"""
    
    def evaluate(self, results: List[Issue], ground_truth: List[Issue]) -> Metrics:
        """
        计算准确性指标：
        - Precision（准确率）：预测的问题中有多少是正确的
        - Recall（召回率）：实际的问题中有多少被发现了
        - F1 Score：准确率和召回率的调和平均
        - False Positive Rate：误报率
        """
        return {
            "precision": self.calculate_precision(results, ground_truth),
            "recall": self.calculate_recall(results, ground_truth),
            "f1_score": self.calculate_f1(results, ground_truth),
            "false_positive_rate": self.calculate_fpr(results, ground_truth),
            "per_rule_metrics": self.calculate_per_rule(results, ground_truth),
        }
```

### 6.2 测试集管理

```
tests/
├── fixtures/                  # 测试样本
│   ├── annotated/             # 已标注样本（ground truth）
│   │   ├── sample_001.pdf    # 标注：issues.json
│   │   └── sample_002.docx
│   └── synthetic/             # 合成的边界样本
│
├── test_parser.py             # 解析器测试
├── test_rule_engine.py        # 规则引擎测试
├── test_llm_client.py         # LLM 客户端测试
├── test_accuracy.py           # 准确性测试
└── test_integration.py        # 集成测试
```

### 6.3 准确率目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Precision（准确率） | ≥ 85% | 误报率 ≤ 15% |
| Recall（召回率） | ≥ 90% | 漏报率 ≤ 10% |
| F1 Score | ≥ 87% | 综合指标 |
| 高风险场景召回率 | ≥ 95% | 高风险必须覆盖 |

### 6.4 定期评估机制

```python
# evaluator/periodic_evaluator.py

class PeriodicEvaluator:
    """
    定期评估机制：
    1. 每次规则更新后评估
    2. 每周增量样本评估
    3. 每月全面评估
    """
    
    def evaluate_after_rule_change(self, rule_id: str):
        """规则变更后评估"""
        
    def schedule_weekly_evaluation(self):
        """每周定时评估"""
        
    def generate_evaluation_report(self) -> Report:
        """生成评估报告"""
```

---

## 7. 监控与可观测性

### 7.1 监控指标

```python
# tracker/metrics.py

class MetricsTracker:
    """关键指标埋点"""
    
    METRICS = {
        # 解析指标
        "parse.success": "解析成功次数",
        "parse.failed": "解析失败次数",
        "parse.duration": "解析耗时",
        
        # 规则引擎指标
        "rule.hit": "规则命中次数",
        "rule.miss": "规则未命中次数",
        "rule.triggered": "各规则触发次数",
        
        # LLM 指标
        "llm.call.success": "LLM 调用成功次数",
        "llm.call.failed": "LLM 调用失败次数",
        "llm.call.timeout": "LLM 调用超时次数",
        "llm.call.duration": "LLM 调用耗时",
        "llm.token.consumed": "Token 消耗量",
        
        # 分析指标
        "analysis.issue.found": "发现的问题数量",
        "analysis.issue.high": "高风险问题数量",
        "analysis.duration": "分析总耗时",
        
        # 报告指标
        "report.generated": "报告生成次数",
        "report.format": "报告格式分布",
    }
```

### 7.2 日志规范

```python
# utils/logging.py

import structlog

# 结构化日志
log = structlog.get_logger()

# 日志规范
"""
日志级别：
- ERROR：系统错误，需要人工介入
- WARNING：异常情况，可能影响功能
- INFO：关键业务流程
- DEBUG：详细调试信息

日志格式（JSON）：
{
    "timestamp": "2026-04-12T15:49:00Z",
    "level": "INFO",
    "event": "analysis.completed",
    "file": "招标文件.pdf",
    "issues_found": 5,
    "duration_ms": 4523,
    "trace_id": "uuid"
}
"""

# 日志脱敏
"""
敏感信息脱敏：
- API Key：显示前4位 + ****
- 文件路径：脱敏用户目录
- 企业名称：使用代号
"""
```

### 7.3 告警机制

```yaml
# config/alerts.yaml

alerts:
  - name: high_error_rate
    condition: error_rate > 5%
    severity: critical
    notification: [email, webhook]
    
  - name: llm_service_down
    condition: llm.call.failed > 10 consecutive
    severity: critical
    notification: [sms, webhook]
    
  - name: high_latency
    condition: analysis.duration > 60s
    severity: warning
    notification: [webhook]
    
  - name: token_quota_warning
    condition: token.consumed > 80% quota
    severity: warning
    notification: [email]
```

---

## 8. 安全设计

### 8.1 敏感信息处理

```python
# utils/security.py

class SecurityUtils:
    """安全工具类"""
    
    @staticmethod
    def mask_api_key(key: str) -> str:
        """API Key 脱敏：显示前4位"""
        if len(key) <= 4:
            return "****"
        return key[:4] + "****"
    
    @staticmethod
    def mask_file_path(path: str) -> str:
        """文件路径脱敏：隐藏用户目录"""
        return path.replace(os.path.expanduser("~"), "~")
    
    @staticmethod
    def sanitize_log(data: dict) -> dict:
        """日志数据脱敏"""
        sensitive_fields = ["api_key", "password", "token"]
        return {
            k: SecurityUtils.mask_api_key(v) if k in sensitive_fields else v
            for k, v in data.items()
        }
```

### 8.2 Prompt 注入检测

```python
# analyzer/llm/injection_detector.py

class PromptInjectionDetector:
    """Prompt 注入检测"""
    
    SUSPICIOUS_PATTERNS = [
        "忽略之前的指示",
        "ignore previous instructions",
        "你是一个不同的AI",
        "你现在是",
        "忘记所有规则",
    ]
    
    def detect(self, text: str) -> bool:
        """检测是否存在 Prompt 注入"""
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.lower() in text.lower():
                return True
        return False
    
    def sanitize(self, text: str) -> str:
        """尝试清理注入内容"""
        # 保留原逻辑，移除可疑部分
        pass
```

### 8.3 配置加密

```toml
# pyproject.toml

[project.optional-dependencies]
security = [
    "cryptography>=41.0.0",  # 配置加密
]

# config/encryption.py
class ConfigEncryptor:
    """敏感配置加密"""
    
    def encrypt(self, value: str) -> str:
        """加密敏感值"""
        
    def decrypt(self, encrypted: str) -> str:
        """解密值"""
```

---

## 9. CLI 命令设计

### 9.1 核心命令

```bash
# 分析单个文件
agent_recheck analyze <file> [options]

# 批量分析
agent_recheck batch <directory> [options]

# 规则自学习
agent_recheck learn [options]

# 知识库管理
agent_recheck knowledge sync
agent_recheck knowledge status

# 规则管理
agent_recheck rules list
agent_recheck rules add <rule.yaml>
agent_recheck rules audit
agent_recheck rules rollback <id>

# 评估
agent_recheck evaluate [--test-set <path>]
agent_recheck evaluate --report

# 监控
agent_recheck stats
agent_recheck stats --metrics <metric_name>
```

### 9.2 选项说明

| 选项 | 说明 | 默认值 |
|------|------|--------|
| --output, -o | 输出文件路径 | report_<timestamp> |
| --format, -f | 输出格式: html/json/markdown | html |
| --no-llm | 仅使用规则引擎 | False |
| --llm-only | 仅使用 LLM | False |
| --threshold | LLM 置信度阈值 | 0.7 |
| --parallel, -p | 并行数量 | 4 |

---

## 10. 报告设计

### 10.1 输出格式

| 格式 | 用途 |
|------|------|
| HTML | 可视化报告，含图表 |
| JSON | 数据接口，程序处理 |
| Markdown | 简洁摘要 |

### 10.2 报告结构

```json
{
  "file": "招标文件.pdf",
  "analyzed_at": "2026-04-12T15:49:00",
  "summary": {
    "total_issues": 5,
    "high_risk": 2,
    "medium_risk": 2,
    "low_risk": 1
  },
  "issues": [
    {
      "id": "R-001",
      "type": "规则匹配",
      "category": "非歧视性",
      "level": "high",
      "title": "限定特定区域业绩",
      "evidence": {
        "quote": "本项目要求供应商具有北京市政府采购业绩",
        "location": {
          "chapter": "第三章",
          "section": "供应商资格条件",
          "article": "第十二条",
          "paragraph": "第2款",
          "page": 8,
          "line_start": 156,
          "line_end": 158
        },
        "highlight": "北京市"
      },
      "rule": {
        "name": "禁止限定特定行政区域业绩",
        "reference": "《政府采购法实施条例》第二十条第四款",
        "full_text": "不得以特定行政区域或者特定行业的业绩..."
      },
      "suggestion": {
        "content": "删除'北京市'限制，修改为'投标截止前3年内...'"
      }
    }
  ],
  "metadata": {
    "knowledge_base_version": "v1.0.20260401",
    "rules_version": "v1.0",
    "llm_model": "qwen3.5-27b",
    "analysis_mode": "hybrid",
    "analysis_duration_ms": 4523
  }
}
```

---

## 11. 知识库设计

### 11.1 目录结构

```
knowledge/
├── regulations/              # 法规原文
│   ├── 政府采购法.md
│   ├── 政府采购法实施条例.md
│   ├── 87号令.md
│   ├── 需求管理办法.md
│   └── regulation_validity.yaml  # 法规有效性状态
├── versions/                 # 版本历史
│   ├── v1.0.20260401/
│   └── v1.1.20260410/
└── sync/                    # 同步工具
    └── sync.py              # 从官网同步
```

### 11.2 知识库版本管理

```yaml
# knowledge/versions/v1.0.20260401/version.yaml

version: v1.0.20260401
created_at: "2026-04-01"
regulations:
  - name: 政府采购法
    checksum: sha256:xxx
  - name: 87号令
    checksum: sha256:yyy
    
description: "初始版本"
```

### 11.3 法规有效性状态

```yaml
regulations:
  - name: 87号令
    status: effective
    effective_date: "2017-10-01"
    
  - name: 财库〔2017〕138号
    status: superseded
    superseded_date: "2021-07-01"
    replaced_by: 政府采购需求管理办法
```

### 11.4 同步来源

| 来源 | 网址 |
|------|------|
| 中国政府采购网 | ccgp.gov.cn |
| 财政部 | mof.gov.cn |
| 中央政府网 | gov.cn |

---

## 12. 技术选型

### 12.1 核心技术栈

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| 语言 | Python 3.10+ | 开发效率高，生态完善 |
| 文档解析 | pdfplumber, PyMuPDF | PDF 解析 |
| 文档解析 | python-docx | Word 解析 |
| 备选解析 | Apache Tika | 通用文档解析 |
| LLM | openai SDK | 兼容 qwen |
| CLI | typer + rich | 命令行界面 |
| 报告 | jinja2 | HTML 模板 |
| 配置 | pyyaml | 规则配置 |
| 日志 | structlog | 结构化日志 |
| 安全 | cryptography | 配置加密 |

### 12.2 依赖清单

```toml
[project]
requires-python = ">=3.10"
dependencies = [
    "pdfplumber>=0.10.0",
    "python-docx>=1.0.0",
    "PyMuPDF>=1.23.0",
    "openai>=1.0.0",
    "pyyaml>=6.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
    "jinja2>=3.1.0",
    "tqdm>=4.65.0",
    "pydantic>=2.0.0",
    "structlog>=23.0.0",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
security = [
    "cryptography>=41.0.0",
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]
```

---

## 13. 实施计划（基于样本分析优化）

### 13.1 优先级调整

根据对深圳10个品目约150份投标文件的分析，调整实施优先级：

| 优先级 | 调整项 | 原因 | 预计工量 |
|--------|--------|------|----------|
| **P0** | 表格解析增强 | 每个文档平均20个表格 | 2周 |
| **P0** | 深圳格式适配 | 深圳特有条例和结构 | 1周 |
| **P1** | 认证证书规则库 | 各品目认证要求差异大 | 2周 |
| **P1** | 评分标准解析 | 权重计算逻辑缺失 | 1周 |
| **P2** | 地方性法规扩展 | 按需支持其他省市 | 持续 |

### 13.2 优化后的实施计划

#### Phase 0: 基础设施（2周）- 新增

| 任务 | 交付物 | 说明 |
|------|--------|------|
| 项目脚手架 | agent_recheck/ | 项目目录结构 |
| 文档解析基础 | parser/ 模块 | PDF/DOCX 基础解析 |
| 表格解析增强 | parser/table_parser | **重点：嵌套表格、标题关联** |
| 深圳格式适配 | parser/shenzhen_adapter | **新增：深圳条例、★▲标记** |

#### Phase 1: 核心能力 (4周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 规则引擎 + 初始规则集（~30条） | engine 模块 | 后端开发 |
| **认证证书规则库** | rules/certifications/ | **优先级提升：按品目分类** |
| LLM 接入 + 容错机制 | llm 模块 | 后端开发 |
| 降级兜底机制 | hybrid_engine | 后端开发 |
| **评分标准解析** | parser/scoring_parser | **新增：权重计算、主观分识别** |
| 基础报告输出 | report 模块 | 后端开发 |
| 单元测试（覆盖率 ≥ 80%） | tests/ | 测试 |

#### Phase 2: 审查能力 (3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 55个场景规则覆盖 | rules/ | 业务专家 |
| 跨段落一致性检查 | consistency 模块 | 后端开发 |
| **深圳知识库构建** | knowledge/regulations/ | **新增：深圳经济特区政府采购条例** |
| 规则审核工作流 | rule_manager | 后端开发 |
| 规则灰度发布 | rule_manager | 后端开发 |
| 解析质量测试集 | tests/fixtures | 测试 |

#### Phase 3: 准确率保障 (2-3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 准确性评估框架 | evaluator 模块 | 后端开发 |
| 测试集标注（20-30份） | tests/fixtures/annotated | 业务专家 |
| 定期评估机制 | periodic_evaluator | 后端开发 |
| 规则质量指标 | evaluator | 后端开发 |

#### Phase 4: 知识库扩展 (2-3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 法规知识库构建 | knowledge/ | 业务专家 |
| 离线同步机制 | sync 模块 | 后端开发 |
| 知识库版本管理 | version_manager | 后端开发 |
| 知识库分发工具 | sync/export | 后端开发 |

#### Phase 5: 生产化 (2-3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 监控埋点 | tracker 模块 | 后端开发 |
| 结构化日志 | utils/logging | 后端开发 |
| 告警机制 | alerts | 运维 |
| 安全设计（日志脱敏、配置加密） | utils/security | 后端开发 |
| 集成测试 | tests/test_integration | 测试 |
| 部署文档 | docs/deployment/ | 运维 |
| 运维手册 | docs/operator/ | 运维 |

### 13.3 下一步行动

基于样本分析，建议按以下顺序启动：

```
1. 表格解析能力开发
   ├── 嵌套表格识别
   ├── 表格标题自动关联
   └── 跨表格数据一致性检查

2. 深圳知识库构建
   ├── 深圳经济特区政府采购条例
   ├── 深圳经济特区政府采购条例实施细则
   └── 评分标准格式定义

3. 认证指向性规则库
   ├── 通用管理体系认证（ISO9001等）
   ├── 行业认证（医疗、家具、物业等）
   └── 证书指向性检测规则
```

---

## 14. 实施计划（原版备查）

### Phase 1: 核心能力 (4-6周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 文档解析（PDF/DOCX） | parser 模块 | 后端开发 |
| 规则引擎 + 初始规则集（~30条） | engine 模块 | 后端开发 |
| LLM 接入 + 容错机制 | llm 模块 | 后端开发 |
| 降级兜底机制 | hybrid_engine | 后端开发 |
| 基础报告输出 | report 模块 | 后端开发 |
| 单元测试（覆盖率 ≥ 80%） | tests/ | 测试 |

### Phase 2: 审查能力 (4周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 55个场景规则覆盖 | rules/ | 业务专家 |
| 跨段落一致性检查 | consistency 模块 | 后端开发 |
| 规则审核工作流 | rule_manager | 后端开发 |
| 规则灰度发布 | rule_manager | 后端开发 |
| HTML 报告优化 | report 模块 | 后端开发 |
| 解析质量测试集 | tests/fixtures | 测试 |

### Phase 3: 准确率保障 (2-3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 准确性评估框架 | evaluator 模块 | 后端开发 |
| 测试集标注（100份） | tests/fixtures/annotated | 业务专家 |
| 定期评估机制 | periodic_evaluator | 后端开发 |
| 规则质量指标 | evaluator | 后端开发 |

### Phase 4: 知识库 (2-3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 法规知识库构建 | knowledge/ | 业务专家 |
| 离线同步机制 | sync 模块 | 后端开发 |
| 知识库版本管理 | version_manager | 后端开发 |
| 知识库分发工具 | sync/export | 后端开发 |

### Phase 5: 生产化 (2-3周)

| 任务 | 交付物 | 负责 |
|------|--------|------|
| 监控埋点 | tracker 模块 | 后端开发 |
| 结构化日志 | utils/logging | 后端开发 |
| 告警机制 | alerts | 运维 |
| 安全设计（日志脱敏、配置加密） | utils/security | 后端开发 |
| 集成测试 | tests/test_integration | 测试 |
| 部署文档 | docs/deployment/ | 运维 |
| 运维手册 | docs/operator/ | 运维 |

---

## 14. 团队分工建议

| 角色 | 人数 | 主要职责 |
|------|------|----------|
| 后端开发 | 2人 | 核心引擎、LLM 封装、规则引擎 |
| 业务专家 | 1人 | 规则编写、样本标注、场景验证 |
| 测试 | 1人 | 测试集、自动化测试、准确率评估 |
| 运维 | 0.5人 | 部署、监控、知识库同步 |

---

## 15. 文档目录

```
docs/
├── architecture.md           # 架构设计文档
├── api.md                    # API 文档（如有）
├── developer.md              # 开发者指南
│
├── rules/                    # 规则编写指南
│   ├── how_to_write_rules.md
│   └── rule_template.yaml
│
├── deployment/               # 部署文档
│   ├── offline_deploy.md     # 离线部署
│   ├── docker_deploy.md      # Docker 部署
│   └── kubernetes_deploy.md   # K8s 部署
│
├── operator/                 # 运维手册
│   ├── troubleshooting.md    # 故障排查
│   ├── knowledge_sync.md     # 知识库同步
│   └── monitoring.md         # 监控配置
│
└── user/                     # 用户手册
    ├── quick_start.md        # 快速入门
    └── command_reference.md  # 命令参考
```

---

## 16. 基于实际样本的发现与架构调整

### 16.1 样本分析结论（深圳家具采购文档）

通过对实际政府采购招标文件样本的分析，验证了架构设计的可行性，并发现以下需要调整的方向：

#### 16.1.1 文档结构特点
- **格式**：DOCX 格式为主
- **结构**：统一采用"专用条款 + 通用条款"结构
- **章节**：包含投标人资格条件、技术需求、评分标准、合同条款等

#### 16.1.2 发现的主要风险点

| 类别 | 风险点 | 说明 |
|------|--------|------|
| 证书指向性 | SA8000认证、企业标准化认证AAAA级 | 特定认证指向特定供应商 |
| 人员资质 | 项目负责人资质要求 | 可能排除中小企业 |
| 业绩要求 | 地域限定业绩 | 违反非歧视性原则 |
| 技术参数 | 特定规格要求 | 可能指向特定品牌 |

### 16.2 架构调整建议

#### 16.2.1 知识库扩展
基于样本分析，需要扩展知识库覆盖范围：

```yaml
knowledge/
├── regulations/              # 法规原文
│   ├── 政府采购法.md
│   ├── 政府采购法实施条例.md
│   ├── 87号令.md
│   ├── 需求管理办法.md
│   ├── 深圳经济特区政府采购条例.md   # 新增：地方性法规
│   └── 省级采购条例/                  # 新增：按需扩展
│
├── certifications/           # 新增：认证证书规则库
│   ├── 国内认证/
│   └── 国际认证/
│
└── sync/                    # 同步工具
```

#### 16.2.2 认证证书指向性规则库

需要建立专门的认证证书审查规则：

```yaml
rules/certifications/
├── 管理体系认证/
│   ├── ISO9001.yaml        # 通用，质量管理体系
│   ├── ISO14001.yaml       # 通用，环境管理体系
│   ├── ISO45001.yaml       # 通用，职业健康安全
│   ├── SA8000.yaml         # 社会责任，需审查指向性
│   └── OHSAS18001.yaml     # 需注意与ISO45001关系
│
├── 企业认证/
│   ├── 高新技术企业.yaml
│   ├── 软件企业.yaml
│   └── 守合同重信用.yaml
│
└── 行业认证/
    ├── 产品认证/           # CCC、节能、环保等
    └── 服务认证/           # 不同行业特殊要求
```

#### 16.2.3 增强表格解析能力

样本中包含大量表格内容，需要增强解析能力：

```python
# analyzer/parser/table_parser.py

class EnhancedTableParser:
    """
    增强型表格解析器
    - 识别嵌套表格
    - 提取表格标题和注释
    - 处理合并单元格
    - 关联表格与上下文段落
    """
    
    def parse_table(self, table_element):
        """解析表格结构"""
        
    def extract_table_metadata(self, table_element):
        """提取表格元信息（标题、编号、注释）"""
        
    def link_table_to_context(self, table, paragraphs):
        """将表格与上下文段落关联"""
```

#### 16.2.4 本地化规则支持

需要支持地方性法规和行业特殊要求：

```python
# analyzer/engine/local_rules.py

class LocalRuleEngine:
    """本地化规则引擎"""
    
    REGION_RULES = {
        "深圳": "深圳经济特区政府采购条例",
        "广东": "广东省政府采购条例",
        "浙江": "浙江省政府采购管理办法",
    }
    
    def get_applicable_rules(self, region: str, industry: str) -> List[Rule]:
        """获取适用的本地化规则"""
```

### 16.3 规则细化示例

#### 16.3.1 认证证书指向性规则

```yaml
rules:
  - id: CERT-001
    name: SA8000认证不得作为准入条件
    category: 非歧视性
    level: high
    
    pattern:
      type: keyword
      match:
        - "SA8000"
        - "社会责任认证"
      context_check: "认证要求.*供应商|供应商.*认证要求"
    
    verification:
      check_type: negative
      scope: [资格条件, 技术要求]
    
    reference:
      law: "政府采购法实施条例"
      article: "第二十条"
      note: "不得以不合理的条件对供应商实行差别待遇或者歧视待遇"
    
    suggestion:
      template: "删除{证书名称}作为资格条件要求，如确需应说明合理理由"
```

#### 16.3.2 人员资质合理性规则

```yaml
rules:
  - id: PERP-001
    name: 项目负责人资质要求不得超出项目需求
    category: 采购需求合理性
    level: medium
    
    pattern:
      type: composite
      conditions:
        - keyword: "项目负责人"
        - level_match: "(高级|正高级|一级).*工程师"
    
    verification:
      check_type: contextual
      consideration:
        - 项目规模和复杂度
        - 资质与工作内容匹配度
        - 行业平均水平
    
    suggestion:
      template: "根据{项目类型}项目的实际需求，合理设置项目负责人资质要求"
```

### 16.4 实施优先级调整

基于样本分析，调整各阶段的实施优先级：

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 表格解析增强 | 样本中大量表格内容 |
| P0 | 认证证书规则库 | 证书指向性风险高发 |
| P1 | 地方性法规支持 | 支持深圳、广东等地 |
| P2 | 行业专用规则 | 按行业逐步扩展 |
| P3 | 跨省一致性 | 全国范围推广时 |

---

## 17. 附录

### 16.1 引用法规

| 法规名称 | 文号 | 施行日期 |
|----------|------|----------|
| 中华人民共和国政府采购法 | 主席令第68号 | 2003-01-01 |
| 中华人民共和国政府采购法实施条例 | 国务院令第658号 | 2015-03-01 |
| 政府采购货物和服务招标投标管理办法 | 财政部令第87号 | 2017-10-01 |
| 政府采购需求管理办法 | 财库〔2021〕22号 | 2021-07-01 |

### 16.2 变更记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-04-12 | 初稿 |
| v1.1 | 2026-04-12 | CTO 审查补充：<br>- 混合分析引擎容错设计<br>- 准确性评估框架<br>- 规则质量把控流程<br>- 监控与可观测性<br>- 安全设计<br>- 团队分工建议<br>- 文档目录完善 |
| v1.2 | 2026-04-12 | 样本分析补充：<br>- 深圳家具采购样本发现<br>- 认证证书指向性规则库<br>- 地方性法规支持（深圳、广东等）<br>- 表格解析能力增强<br>- 实施优先级调整 |
| v1.3 | 2026-04-12 | 架构评估结论落地：<br>- 新增第13.1章：基于样本分析的优先级调整<br>- 新增Phase 0：表格解析+深圳格式适配<br>- 调整Phase 1-5任务和优先级<br>- 新增第13.3章：下一步行动指引 |
