# agent_recheck

政府采购招投标文件合规性审查智能体

## 功能特性

- 🤖 **AI 智能审查**：基于 LLM 的深度语义分析
- 📋 **规则引擎**：55+ 合规性检测规则
- 🔄 **混合分析**：规则引擎 + AI 双重保障
- 📊 **结构化报告**：精准定位风险点，提供修改建议
- 🔒 **离线支持**：适配隔离内网环境

## 快速开始

### 安装

```bash
# 从源码安装
cd agent_recheck
pip install -e .

# 或安装开发版本
pip install -e ".[dev]"
```

### 配置

```bash
# 复制配置模板
cp config/default.yaml.example config/default.yaml

# 编辑配置
vim config/default.yaml
```

### 使用

```bash
# 分析单个文件
agent_recheck analyze document.docx

# 批量分析
agent_recheck batch ./documents/

# 查看规则列表
agent_recheck rules list

# 评估准确性
agent_recheck evaluate --test-set ./tests/fixtures/annotated/
```

## 项目结构

```
agent_recheck/
├── cli/              # 命令行入口
├── analyzer/         # 核心分析引擎
│   ├── parser/       # 文档解析
│   ├── engine/       # 规则引擎
│   └── llm/          # LLM 集成
├── rules/            # 规则配置
├── knowledge/         # 知识库
├── report/           # 报告生成
└── tests/            # 测试
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
ruff format .

# 类型检查
mypy .
```

## 许可

MIT License
