# Phase 0 Research: AIExport

**Feature**: AI 导出与分析系统
**Date**: 2026-06-22

## Research Items

### R1: SQL Server Python 连接库选型

**Decision**: pymssql（首选），pyodbc（备选）

**Rationale**:
- pymssql 基于 FreeTDS，纯 Python 绑定，`pip install pymssql` 即可使用
- pyodbc 需要系统安装 ODBC Driver 17 for SQL Server，Windows 上常见但 Linux 需要额外配置
- 两者性能差异微小（<5%），API 都支持参数化查询（防 SQL 注入）

**Alternatives considered**:
- SQLAlchemy + mssql 方言：功能过剩，本项目只需执行原始 SQL，不需要 ORM
- adodbapi（仅 Windows）：跨平台受限

### R2: 模版匹配算法

**Decision**: 双阶段匹配：精确匹配 + 模糊容差

**Rationale**:
- 阶段1（精确匹配）：门店名称 + 员工ID 作为复合键，直接 pandas merge
- 阶段2（容差匹配）：对未匹配的员工，尝试仅员工ID 匹配（跨店员工），日志警告
- 匹配复杂度 O(n)（哈希表），5000 行数据 < 1 秒

**Alternatives considered**:
- 模糊字符串匹配（fuzzywuzzy/thefuzz）：门店名通常无拼写差异，模糊匹配引入不确定性

### R3: Excel 生成库

**Decision**: openpyxl

**Rationale**:
- 读写 .xlsx 的纯 Python 库，无外部依赖
- 支持单元格样式（加粗、对齐、数字格式）
- 读写性能足够（5000 行数据 < 2 秒）
- pandas 内置 `to_excel` 使用 openpyxl 引擎

**Alternatives considered**:
- xlsxwriter：写性能更好但不支持读取
- xlwings：依赖 Excel 应用程序（Windows/Mac 独占，需要安装 Excel）

### R4: CLI 框架

**Decision**: click

**Rationale**:
- 成熟、稳定，Python 社区标准
- 装饰器风格简洁：`@click.command()`
- 自动生成 `--help` 文档
- 支持子命令组、参数类型验证、回调函数

**Alternatives considered**:
- argparse：标准库但样板代码多
- typer：基于类型提示，更现代但依赖 click，本质是 click 的超集

### R5: 大数据量扩展方案

**Decision**: 当前不实现，预留扩展点

**Rationale**: spec 明确数据量 < 10 万行。如果未来需要：
- pandas chunksize 分批读取 SQL 结果
- 分析阶段用分组合并（groupby 流式处理）
- 切换 adapter 即可，不影响分析核心逻辑

### R6: 配置文件 Schema 校验

**Decision**: 自定义校验函数 + dataclass 类型转换

**Rationale**:
- 配置字段可控（<15 个必填字段），不需要引入 JSON Schema
- dataclass 自动提供 `__init__` 类型转换和字段默认值
- 校验失败返回明确的字段名+错误描述

**Alternatives considered**:
- pydantic：功能强大但引入额外依赖，字段少时过度设计
- JSON Schema + jsonschema：不如直接 Python 校验直观

### R7: 中文编码兼容性

**Decision**: UTF-8 for .xlsx (openpyxl 原生 Unicode)、UTF-8 (no BOM) for .md

**Rationale**:
- .xlsx (openpyxl) 内置 Unicode 支持，无需 BOM
- .md 文件使用 UTF-8 (no BOM)，GitHub/GitLab/IDE 通用
- .yaml 配置文件使用 UTF-8 (no BOM)
- 原本 spec 中 CSV 的 BOM 问题已不再适用（改为 .xlsx）

### R8: 数据库密码安全策略

**Decision**: 强制 `${ENV_VAR}` 环境变量引用，拒绝纯文本密码

**Rationale**:
- 配置文件可能被误提交到版本控制（即使 .gitignore 了 export.yaml）
- 环境变量是运维安全基线（12-Factor App 原则）
- `_resolve_env_vars()` 函数解析 `${DB_PASSWORD}` → `os.environ.get("DB_PASSWORD")`
- 启动时若环境变量不存在，密码字段为空字符串，SQL Server 连接将失败并返回明确错误

**Alternatives considered**:
- .env 文件 + python-dotenv：增加依赖，且 .env 文件同样可能泄露
- 系统密钥环（keyring）：平台依赖过重，CLI 工具过度设计
- 明文允许（原方案）：安全风险不可接受

## Summary

所有 NEEDS CLARIFICATION 均已解决。技术栈选型确定：
- **pymssql** + **pandas** + **openpyxl** + **click** + **structlog**
- 全部纯 Python 依赖，跨平台（Windows/Linux）
- 当前数据量级无需流式处理，预留扩展点即可
