---
name: session-summary-20260622
description: Full session state for AIExportNew project — resume point after context limit
metadata:
  type: project
---

## AIExportNew 项目当前状态

**Branch**: AIExportNew
**Constitution**: v1.1.0 (6 core principles including TDD)
**Last run**: 2026-06-22 13:59 — pipeline SUCCESS

### 上次运行结果

- 711 rows exported from SQL Server (Xinglin.YaoAn)
- Chain total: ¥150,198.08
- Template matched: 61/78 employees
- Template employee total: ¥73,955.00 (49.24%)
- 17 employees had no sales in the period
- Pipeline completed in 0.6s

### 数据库配置 (configs/export.yaml)

- Server: `.`
- Database: `Xinglin.YaoAn`
- Username: `sa`
- Password: `${DB_PASSWORD}` (env var, currently set to "1")
- Enterprise ID: `68288c8975fb4fa1a4b94da70b9f2765`
- Date range: 2026-06-01 ~ 2026-06-16
- Staff IDs: 78 employee IDs matching the template
- Medicine IDs: 19 IDs for Xinglin.YaoAn

### 项目结构

- `src/` — 6 modules: config, export, template, analysis, report, pipeline, cli
- `configs/templates/` — 2 templates: sanzhen-jiuti (78 employees), monthly-summary (10 stores)
- `tests/` — 7 test files, 41 tests, all passing
- `specs/001-ai-export-analysis/` — 10 spec documents (spec, prd, tdd-tests, plan, design, data-model, research, quickstart, tasks, checklists)

### Known issues / todo

1. 17 template employees not matched in Xinglin.YaoAn — need to update template or staff list
2. pytest.ini has `--strict-markers` which may cause warnings; can remove if needed
3. Git commit `306172d` pushed to GitHub — PR ready

### 常用命令

```bash
python -m src.cli validate             # 校验所有配置
python -m src.cli run -t sanzhen-jiuti # 一键全流程
python -m src.cli list-templates       # 列模版
python -m pytest tests/ -q            # 运行41个测试
```

### 环境变量

- `DB_PASSWORD=1` (PowerShell: `$env:DB_PASSWORD = "1"`)
