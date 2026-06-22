# Implementation Plan: AI 导出与分析系统（AIExport）

**Branch**: `AIExportNew` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-ai-export-analysis/spec.md`

## Summary

实现后端 AI 导出与分析系统，支持从 SQL Server 导出销售明细数据（.xlsx）、按可配置模版（如"三诊九体培训动销"）进行分组汇总和占比分析，最终生成 Markdown 分析报告和 Excel 数据表格。全部功能通过 CLI 命令驱动，纯后端实现。

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: pandas, openpyxl, pymssql, pyyaml, click, structlog

**Storage**: 文件系统 — YAML 配置、.xlsx 数据文件、.md/.xlsx 报告

**Testing**: pytest + pytest-cov + pytest-mock

**Target Platform**: Windows Server / Linux Server

**Project Type**: CLI tool

**Performance Goals**: 5000 行数据全流程 < 30 秒

**Constraints**: 纯后端无前端、UTF-8 编码、参数化查询防 SQL 注入、密码 MUST 使用 `${ENV_VAR}` 环境变量引用（禁止明文）

**Scale/Scope**: 单机运行、10 万行以内数据、10+ 模版注册

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First | ✅ PASS | spec.md 已创建并通过质量检查 |
| II. Simplicity by Default | ✅ PASS | 每个模块职责单一：config → export → analyze → report |
| III. Think Before Coding | ✅ PASS | 所有技术决策在本文档中显式声明 |
| IV. Surgical Changes | ✅ PASS | 纯新功能，无现有代码需要修改 |
| V. Goal-Driven Execution | ✅ PASS | TDD 测试用例已定义（tdd-tests.md） |
| VI. TDD (NON-NEGOTIABLE) | ✅ PASS | 41 个 pytest 测试全部通过，先写测试后实现，Red-Green-Refactor 循环执行 |

| Technical Constraint | Status | Evidence |
|----------------------|--------|----------|
| AI Model Portability | ⬚ N/A | 本功能不涉及 AI 调用（纯数据导出+模版匹配+报告生成），约束不适用 |
| Report Multi-format | ✅ PASS | Markdown + Excel 满足宪法"where applicable"多格式要求；HTML/PDF 非当前药房销售分析场景必需 |
| Observability | ✅ PASS | structlog 全流程结构化日志（输入/输出/耗时/匹配率） |
| Error Handling | ✅ PASS | 异常翻译为用户可读中文错误信息，5 秒内返回 |

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-export-analysis/
├── plan.md              # 本文件
├── spec.md              # 功能规格说明
├── prd.md               # 产品需求文档
├── tdd-tests.md         # TDD 测试用例
├── design.md            # 设计规范文档
├── research.md          # Phase 0 研究输出
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # 快速启动指南
└── checklists/
    └── requirements.md  # 规格质量检查清单
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── loader.py         # YAML/JSON 配置加载
│   ├── validator.py      # 配置 Schema 校验
│   └── models.py         # 配置实体模型
├── export/
│   ├── __init__.py
│   ├── connector.py      # SQL Server 连接管理
│   ├── executor.py       # 查询执行 + .xlsx 写入
│   └── writer.py         # .xlsx 文件工具
├── analysis/
│   ├── __init__.py
│   ├── engine.py         # 模版匹配与分析引擎
│   ├── matcher.py        # 员工/门店匹配逻辑
│   └── calculator.py     # 汇总/占比计算
├── report/
│   ├── __init__.py
│   ├── markdown.py       # Markdown 报告生成
│   └── excel.py          # Excel 报告生成
├── template/
│   ├── __init__.py
│   ├── registry.py       # 模版注册表
│   └── models.py         # 模版实体模型
├── cli.py                # CLI 命令入口 (click)
└── pipeline.py           # 全流程编排

configs/
├── export.yaml           # 导出配置（SQL连接+查询）
└── templates/
    ├── sanzhen-jiuti.yaml     # "三诊九体培训动销"模版
    └── monthly-summary.yaml   # 月度销售汇总模版（示例）

tests/
├── __init__.py
├── conftest.py           # pytest fixtures & mocks
├── test_config.py
├── test_export.py
├── test_analysis.py
├── test_report.py
├── test_cli.py
└── test_edge_cases.py

output/                   # 运行时输出（gitignore）
├── exports/              # 导出的 .xlsx 数据
└── reports/              # .md + .xlsx 报告
```

**Structure Decision**: 选择单项目结构 — `src/` + `tests/` 分层，因为这是纯 CLI 工具，不需要前后端分离。

## Complexity Tracking

> 宪法约束澄清记录（非违规）

| 约束 | 判定 | 理由 |
|------|------|------|
| AI Model Portability | N/A | 功能不涉及 AI 调用：数据导出→模版匹配→报告生成均为确定性计算，无 LLM/模型调用点 |
| Report Multi-format (HTML/PDF) | 延后 | 当前交付 Markdown + Excel；宪法"where applicable"条款下 HTML/PDF 非药房销售分析必需格式，若未来需要 Web 报告可追加 |

## Technical Decisions Reference

| # | 决策点 | 选择 | 理由 |
|---|--------|------|------|
| D1 | SQL Server 连接 | pymssql（首选）/ pyodbc（备选） | FreeTDS 绑定，无需 ODBC 驱动安装 |
| D2 | 配置格式 | YAML | 人工可读写，支持注释 |
| D3 | CLI 框架 | click | 装饰器风格，参数验证+帮助生成 |
| D4 | 数据处理 | pandas DataFrame | 内存计算，当前数据量级足够 |
| D5 | Excel 生成 | openpyxl | 纯 Python，跨平台，格式化能力强 |
| D6 | 日志 | structlog | 结构化日志，JSON/文本双模式 |
| D7 | 密码安全 | `${ENV_VAR}` 环境变量引用 + 明文拒绝 | 配置可能误提交版本控制，环境变量隔离敏感信息 |
| D8 | 未匹配数据 | 单独列出不计入合计 | 保持模版评估目标群体纯度，避免未知数据污染占比较准 |
