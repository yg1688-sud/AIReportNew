# Tasks: AI 导出与分析系统（AIExport）

**Input**: `specs/001-ai-export-analysis/spec.md`, `plan.md`, `data-model.md`

**Prerequisites**: ✅ spec.md, plan.md, data-model.md, research.md

**Clarifications Applied**: FR-001 密码强制 `${ENV_VAR}` | FR-010 未匹配数据不计入合计

---

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to user story (US1–US4) from spec.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per plan.md (`src/`, `tests/`, `configs/`, `output/`)
- [x] T002 [P] Create `requirements.txt` with dependencies: pandas, openpyxl, pymssql, pyyaml, click, structlog, pytest, pytest-cov, pytest-mock
- [x] T003 [P] Create `src/__init__.py` and all package `__init__.py` files (`config/`, `export/`, `analysis/`, `report/`, `template/`)

---

## Phase 2: Foundational — Config Module (Blocking Prerequisites)

**Purpose**: Configuration loading and validation — ALL user stories depend on this

**⚠️ CRITICAL**: No user story can begin until config models, loader, and validator are complete.

- [x] T004 [P] Implement `src/config/models.py` — all dataclasses: ExportConfig, AnalysisTemplate, TemplateColumn, MatchKey, SortRule, SummaryRule, EmployeeRow, ExportResult, AnalysisRow, AnalysisTotal, AnalysisMetadata, AnalysisResult, AnalysisReport
- [x] T005 [P] Implement `src/config/loader.py` — YAML→Python object conversion; `_resolve_env_vars()` for `${ENV_VAR}` password resolution; `load_export_config()`, `load_template()`
- [x] T006 Implement `src/config/validator.py` — Schema validation: required fields, port range (1–65535), timeout (5–300), `${ENV_VAR}` password enforcement (reject plaintext), template employee_id uniqueness, match_key field count alignment, SQL safety check

**Checkpoint**: Config load/validate working — user story implementation can now begin

---

## Phase 3: User Story 1 — 配置化数据导出 (Priority: P1) 🎯 MVP

**Goal**: 系统管理员通过 YAML 配置定义 SQL 查询，系统自动导出为 .xlsx 文件

**Independent Test**: `python -m src.cli export` → 验证 output/exports/ 目录生成 .xlsx 文件

### Implementation for User Story 1

- [x] T007 [P] [US1] Implement `src/export/connector.py` — `SQLServerConnector` class: pymssql context manager, `execute()` with parameterized queries, `fetch_all_as_dicts()`, `fetch_value()`, ConnectionError on failure, charset=UTF-8
- [x] T008 [P] [US1] Implement `src/export/writer.py` — `write_to_excel()`: pandas `to_excel()` with openpyxl engine, auto column-width adjustment, timestamped filenames, output directory auto-creation
- [x] T009 [US1] Implement `src/export/executor.py` — `execute_export()`: resolve `{{param}}` placeholders, execute detail + summary queries via SQLServerConnector, build DataFrame, call write_to_excel(), return ExportResult with row count/timing
- [x] T010 [P] [US1] Create `configs/export.yaml` — SQL Server connection params, detail_query + summary_query with `{{param}}` placeholders, parameters dict (enterprise_id, start_date, end_date, medicine_ids, staff_ids), timeout, output_dir

**Checkpoint**: Export works standalone — `python -m src.cli export` produces .xlsx

---

## Phase 4: User Story 2 — 模版化数据分析 (Priority: P1) 🎯 MVP

**Goal**: 业务分析师选定模版，系统自动按片区→门店→员工汇总销售金额并计算占比

**Independent Test**: 提供 .xlsx 数据 + 模版 YAML → 验证输出 AnalysisResult 行数/合计/占比正确

### Implementation for User Story 2

- [x] T011 [P] [US2] Implement `src/template/registry.py` — `TemplateRegistry` class: scan `configs/templates/*.yaml`, `get(name)`, `list_all()`, `refresh()` for hot-reload, TemplateNotFoundError
- [x] T012 [P] [US2] Implement `src/analysis/matcher.py` — `match_employees()`: exact match on employee_id (string-normalized), sum multiple rows per employee, unmatched template rows → sales=0 + matched=False, unmatched data rows → separate list (NOT in totals per FR-010), log match rate
- [x] T013 [P] [US2] Implement `src/analysis/calculator.py` — `calculate_percentages()`: each employee / total_sales × 100, precision 2 decimals; `calculate_total()`: aggregate total_sales, count active employees, count unique stores
- [x] T014 [US2] Implement `src/analysis/engine.py` — `run_analysis()`: orchestrate match → percentage → total, execute summary_query for chain total, handle summary query failure (fallback to employee sum), return AnalysisResult with metadata
- [x] T015 [P] [US2] Create `configs/templates/sanzhen-jiuti.yaml` — full "三诊九体培训动销及打卡学习情况" template: 78 employees with seq/area/store/name/employee_id/department, columns defs (8 cols), match_key (employee_id → 销售店员ERPID), group_by/ sort_by/ summary_rules
- [x] T016 [P] [US2] Create `configs/templates/monthly-summary.yaml` — sample "月度销售汇总" template: 10 stores, store-level aggregation (no employee dimension), different group_by config

**Checkpoint**: Analysis works standalone — `python -m src.cli analyze -t sanzhen-jiuti -d data.xlsx`

---

## Phase 5: User Story 3 — 分析结果导出与报告生成 (Priority: P2)

**Goal**: 系统自动将分析结果生成 Markdown 报告和格式化 Excel 表格

**Independent Test**: 提供 AnalysisResult → 验证 output/reports/ 下生成 .md + .xlsx 文件，可直接打开

### Implementation for User Story 3

- [x] T017 [P] [US3] Implement `src/report/markdown.py` — `generate_markdown_report()`: render Markdown with title (含日期范围), 汇总统计(总销售额/员工数/门店数/匹配率), 详细分析表格, 合计行, 未匹配数据附录, UTF-8 encoding
- [x] T018 [P] [US3] Implement `src/report/excel.py` — `generate_excel_report()`: openpyxl formatted workbook, merged title row, bold headers with fill, money format (#,##0.00), percent format (0.00%), right-aligned numbers, zero-sales rows grayed out, auto column widths, thin borders

**Checkpoint**: Reports generate standalone

---

## Phase 6: User Story 4 — 多模版管理与切换 (Priority: P3)

**Goal**: 系统管理员注册多个模版，不同模版之间独立执行、互不干扰

**Independent Test**: 注册2个模版 → 分别执行分析 → 验证两份结果结构不同且各自正确

### Implementation for User Story 4

- [x] T019 [US4] Update `src/template/registry.py` — ensure hot-reload via `refresh()` works correctly; validate that templates with different group_by / match_key / columns produce structurally correct but independent results
- [x] T020 [US4] Update `src/cli.py` `list-templates` command — display template name + display_name + description for each registered template

**Checkpoint**: Multi-template verified — `python -m src.cli list-templates` shows all; switching templates works

---

## Phase 7: Pipeline + CLI (流程编排)

**Purpose**: Wire all modules together; expose as CLI

- [x] T021 Implement `src/pipeline.py` — `run_full_pipeline()`: config load → export → analyze → markdown report → excel report, structured logging at each stage, elapsed timing, PipelineError on stage failure
- [x] T022 Implement `src/cli.py` — Click CLI group with commands: `run` (--template, --config, --date-start, --date-end), `export` (--config), `analyze` (--template, --data), `list-templates`, `validate` (--config-dir); print ✅ status per stage, exit code 1 on error

**Checkpoint**: Full pipeline end-to-end — `python -m src.cli run -t sanzhen-jiuti`

---

## Phase 8: Tests (TDD)

**Purpose**: Validate all modules per tdd-tests.md test cases

- [x] T023 [P] Implement `tests/conftest.py` — Shared fixtures: mock_sql_connection (pymssql mock), sample order data factory, mock analysis result factory, temp directories
- [x] T024 [P] Implement `tests/test_config.py` — TC-CFG-001: valid config load, TC-CFG-002: missing file error, TC-CFG-003: missing field validation, TC-CFG-004: template load, TC-CFG-005: password `${ENV_VAR}` enforcement (reject plaintext)
- [x] T025 [P] Implement `tests/test_export.py` — TC-EXP-001: export to .xlsx, TC-EXP-002: empty result, TC-EXP-003: connection failure, TC-EXP-004: query timeout, TC-EXP-005: param resolution, TC-EXP-006: SQL injection prevention, TC-EXP-007: column detection
- [x] T026 [P] Implement `tests/test_analysis.py` — TC-ANL-001: group & sum, TC-ANL-002: total matches, TC-ANL-003: percentage calc, TC-ANL-004: percentages sum to 100%, TC-ANL-005: template employee not in data → zero, TC-ANL-006: data employee not in template → unmatched list (not in totals), TC-ANL-007: unmatched excluded from totals, TC-ANL-008: sort order preserved
- [x] T027 [P] Implement `tests/test_report.py` — TC-RPT-001: markdown structure, TC-RPT-002: row count matches, TC-RPT-003: excel format, TC-RPT-004: zero-sales employee in report, TC-RPT-005: excel file validity
- [x] T028 [P] Implement `tests/test_cli.py` — TC-CLI-001: run full pipeline, TC-CLI-002: list-templates, TC-CLI-003: validate passes, TC-CLI-004: validate detects errors
- [x] T029 [P] Implement `tests/test_edge_cases.py` — TC-EDGE-001: 5000-row performance <30s (SC-001), TC-EDGE-002: date boundary inclusive/exclusive, TC-EDGE-003: employee_id type normalization (str vs int), TC-EDGE-004: NULL values in query result, TC-EDGE-005: missing password env var error message, TC-EDGE-006: per-employee SQL comparison (SC-003 — each employee sales matches direct SQL query), TC-EDGE-007: 10-template registration capacity (SC-004), TC-EDGE-008: config error returns within 5s (SC-006)

---

## Dependencies & Execution Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Config) ←── FOUNDATIONAL: blocks ALL user stories
    ↓
    ├─ Phase 3 (US1: Export) ────┐
    ├─ Phase 4 (US2: Analysis) ──┤── Can run in parallel after Phase 2
    ├─ Phase 5 (US3: Report) ────┤
    └─ Phase 6 (US4: Multi-Tmpl)─┘
    ↓
Phase 7 (Pipeline + CLI) ←── Depends on US1–US3 complete
    ↓
Phase 8 (Tests) ←── Can be written alongside implementation
```

### User Story Dependencies

- **US1 (Export)**: Depends on Phase 2 only — no dependency on other stories
- **US2 (Analysis)**: Depends on Phase 2 + US1 data format — independently testable with mock data
- **US3 (Report)**: Depends on US2 (needs AnalysisResult) — independently testable with mock result
- **US4 (Multi-Template)**: Depends on US2 (template registry) — adds capability without blocking others

### Within Each User Story

- Models/Types → Implementation → Config files (where applicable)
- [P] tasks can be done in parallel within the same story

### Parallel Opportunities

| Phase | Parallel Tasks |
|-------|---------------|
| Phase 1 | T002 ∥ T003 |
| Phase 2 | T004 ∥ T005 |
| Phase 3 | T007 ∥ T008 ∥ T010 |
| Phase 4 | T011 ∥ T012 ∥ T013 ∥ T015 ∥ T016 |
| Phase 5 | T017 ∥ T018 |
| Phase 8 | T023–T029 all parallel |

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Config (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (Export)
4. Complete Phase 4: US2 (Analysis)
5. **STOP and VALIDATE**: `python -m src.cli analyze -t sanzhen-jiuti -d output/exports/export_result_*.xlsx`
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Config → Foundation ready
2. US1 → Export data to .xlsx (deliverable: raw data)
3. US2 → Analyze with template (deliverable: structured results)
4. US3 → Generate reports (deliverable: .md + .xlsx reports)
5. US4 → Multi-template (deliverable: extensible template system)
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [USx] label maps task to user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Password security**: All tasks involving config MUST enforce `${ENV_VAR}` per FR-001
- **Unmatched data**: Analysis tasks MUST exclude unmatched data from totals per FR-010
