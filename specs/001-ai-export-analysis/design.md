# AIExport 功能设计规范

**版本**: 1.0.0
**创建日期**: 2026-06-22
**关联**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md)

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                     CLI Layer (click)                 │
│  ai-export run|export|analyze|report|list-templates   │
├──────────┬──────────┬──────────┬─────────────────────┤
│  Config   │ Export   │ Analysis │ Report              │
│  Module   │ Module   │ Module   │ Module              │
├──────────┼──────────┼──────────┼─────────────────────┤
│ loader    │ connector│ engine   │ markdown            │
│ validator │ executor │ matcher  │ excel               │
│ models    │ writer   │ calculator│                   │
├──────────┴──────────┴──────────┴─────────────────────┤
│                  Template Registry                    │
├──────────────────────────────────────────────────────┤
│              Pipeline (全流程编排)                     │
├──────────────────────────────────────────────────────┤
│              structlog (结构化日志)                    │
└──────────────────────────────────────────────────────┘
```

## 2. 模块详细设计

### 2.1 Config 模块（src/config/）

**职责**: 配置文件的加载、校验、类型转换。

**文件结构**:
- `models.py` — dataclass 定义（ExportConfig, AnalysisTemplate 等）
- `loader.py` — YAML 文件 → Python 对象
- `validator.py` — Schema 校验，字段类型/范围检查

**加载流程**:
```
config.yaml → yaml.safe_load() → dict → ExportConfig(**dict)
template.yaml → yaml.safe_load() → dict → AnalysisTemplate(**dict)
```

**校验流程**:
```
ExportConfig → validate_required_fields() → validate_port_range() → validate_sql_safety()
AnalysisTemplate → validate_columns() → validate_match_key() → validate_employee_list()
```

**错误处理**:
```python
class ConfigValidationError(Exception):
    """配置校验错误"""
    def __init__(self, file_path: str, field: str, message: str):
        self.file_path = file_path
        self.field = field
        self.message = message
        super().__init__(f"{file_path}: {field} — {message}")
```

### 2.2 Export 模块（src/export/）

**职责**: SQL Server 连接管理、查询执行、结果写入 .xlsx。

**文件结构**:
- `connector.py` — 连接池管理，上下文管理器
- `executor.py` — 参数化查询执行
- `writer.py` — DataFrame → .xlsx 文件

**连接管理**:
```python
class SQLServerConnector:
    """pymssql 连接封装"""
    def __enter__(self) -> pymssql.Connection:
        self.conn = pymssql.connect(
            server=self.config.server,
            port=self.config.port,
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            login_timeout=self.config.timeout,
            charset='UTF-8',
        )
        return self.conn

    def __exit__(self, ...):
        self.conn.close()
```

**查询执行**:
```python
def execute_parameterized_query(
    connector: SQLServerConnector,
    query: str,
    params: dict[str, str],
) -> pd.DataFrame:
    """
    使用参数化查询执行 SQL。
    1. 解析 {{param}} 占位符 → 构建参数化 SQL
    2. 使用 pymssql 的 %s 占位符传递参数值
    3. 返回 pandas DataFrame
    """
```

**安全设计（防 SQL 注入）**:
```python
# 错误做法（字符串拼接）：
sql = query.replace("{{start_date}}", f"'{user_input}'")  # ❌ 可注入

# 正确做法（参数化查询）：
# 1. 将 {{param}} 替换为数据库驱动的参数占位符（pymssql: %s）
# 2. 将参数值作为 tuple 传递给 cursor.execute()
sql = "SELECT ... WHERE date >= %s AND date < %s"
cursor.execute(sql, (start_date, end_date))  # ✅ 防注入
```

**导出结果格式**:
- 导出为 `.xlsx`，使用 pandas `to_excel()` 引擎
- 文件名: `{export_filename}_{timestamp}.xlsx`
- 编码: openpyxl 内置 UTF-8 支持

### 2.3 Template 模块（src/template/）

**职责**: 模版的注册、加载、查询。

**文件结构**:
- `models.py` — TemplateColumn, SortRule, MatchKey, SummaryRule, EmployeeRow
- `registry.py` — 模版注册表

**模版注册表设计**:
```python
class TemplateRegistry:
    """模版注册表，支持多模版管理"""
    
    def __init__(self, templates_dir: str = "configs/templates"):
        self._templates: dict[str, AnalysisTemplate] = {}
        self._load_all(templates_dir)
    
    def _load_all(self, dir: str):
        """扫描目录，加载所有 .yaml 文件"""
        for yaml_file in Path(dir).glob("*.yaml"):
            template = load_template(str(yaml_file))
            self._templates[template.name] = template
    
    def get(self, name: str) -> AnalysisTemplate:
        """获取指定模版"""
        if name not in self._templates:
            raise TemplateNotFoundError(name)
        return self._templates[name]
    
    def list_all(self) -> list[str]:
        """列出所有模版名称"""
        return list(self._templates.keys())
    
    def refresh(self):
        """重新加载所有模版（无需重启）"""
        self._templates.clear()
        self._load_all(self.templates_dir)
```

### 2.4 Analysis 模块（src/analysis/）

**职责**: 模版匹配、数据分组汇总、占比计算。

**文件结构**:
- `engine.py` — 分析引擎主入口
- `matcher.py` — 员工/门店匹配逻辑
- `calculator.py` — 汇总计算（sum、percentage）

**分析流程**:
```
1. 加载原始数据 (pd.DataFrame from .xlsx)
2. 加载分析模版 (AnalysisTemplate)
3. 数据清洗：
   - 移除 NULL 行
   - 统一员工ID 类型为 str
   - 确保金额列类型为 float
4. 模版匹配（matcher.match）：
   对每个 EmployeeRow:
     - 在 DataFrame 中查找 match_key 匹配的行
     - 找到 → 分组汇总销售金额
     - 未找到 → sales_amount = 0
5. 计算占比（calculator.calculate_percentage）：
   - total_sales = summary_query 执行结果
   - 每员工占比 = employee_sales / total_sales * 100
6. 计算合计行
7. 生成 AnalysisResult
```

**匹配策略（matcher.py）**:
```python
def match_employee_to_data(
    template: AnalysisTemplate,
    data: pd.DataFrame,
) -> tuple[list[AnalysisRow], list[dict]]:
    """
    双阶段匹配：
    Phase 1: 精确匹配 (门店 + 员工ID)
    Phase 2: 容差匹配 (仅员工ID) — 用于调店员工
    
    Returns: (matched_rows, unmatched_data_rows)
    """
    matched = []
    unmatched_data_indices = set(data.index)
    
    for employee in template.employee_list:
        mask = (
            (data["销售店员ERPID"].astype(str) == employee.employee_id)
        )
        matched_data = data[mask]
        
        if len(matched_data) > 0:
            sales_sum = matched_data["销售金额"].sum()
            unmatched_data_indices -= set(matched_data.index)
            matched.append(AnalysisRow(
                seq=employee.seq,
                area=employee.area,
                store=employee.store,
                name=employee.name,
                employee_id=employee.employee_id,
                sales_amount=round(sales_sum, 2),
                department=employee.department,
                matched=True,
            ))
        else:
            matched.append(AnalysisRow(
                seq=employee.seq,
                area=employee.area,
                store=employee.store,
                name=employee.name,
                employee_id=employee.employee_id,
                sales_amount=0.0,
                department=employee.department,
                matched=False,
            ))
    
    # 未匹配的数据行
    unmatched = data.loc[list(unmatched_data_indices)].to_dict("records")
    
    return matched, unmatched
```

**计算逻辑（calculator.py）**:
```python
def calculate_percentages(
    rows: list[AnalysisRow],
    total_sales: float,
) -> list[AnalysisRow]:
    """计算每个员工的销售占比"""
    for row in rows:
        if total_sales > 0:
            row.percentage = round((row.sales_amount / total_sales) * 100, 2)
        else:
            row.percentage = 0.0
    return rows

def calculate_total(rows: list[AnalysisRow]) -> AnalysisTotal:
    """计算合计行"""
    return AnalysisTotal(
        total_sales=sum(r.sales_amount for r in rows),
        total_employees=sum(1 for r in rows if r.sales_amount > 0),
        total_stores=len(set(r.store for r in rows)),
    )
```

### 2.5 Report 模块（src/report/）

**职责**: Markdown 和 Excel 报告生成。

**文件结构**:
- `markdown.py` — Markdown 报告模板与生成
- `excel.py` — Excel 报告格式与生成

**Markdown 报告模板**:
```python
MARKDOWN_REPORT_TEMPLATE = """
# {display_name}

**分析期间**: {start_date} 至 {end_date}
**生成时间**: {generated_at}
**模版**: {template_name}

---

## 汇总统计

| 指标 | 值 |
|------|-----|
| 连锁月度总销售额 | ¥{total_sales:,.2f} |
| 有销售记录员工数 | {active_employees} / {total_employees} |
| 覆盖门店数 | {total_stores} |

---

## 详细分析

| 序号 | 片区 | 门店 | 姓名 | 员工ID | 销售金额 | 占比 | 部门 |
|------|------|------|------|--------|----------|------|------|
{detail_rows}

---

*报告由 AIExport 自动生成*
"""
```

**Excel 报告格式**:
```python
def generate_excel_report(result: AnalysisResult, filepath: str):
    """生成格式化 Excel 报告"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = result.template_name
    
    # 标题行（合并单元格）
    ws.merge_cells('A1:H1')
    ws['A1'] = f"{result.template_name}（{date_range}）"
    ws['A1'].font = Font(bold=True, size=14)
    
    # 表头行
    headers = ["序号", "片区", "门店", "姓名", "员工ID", "销售金额", "占比", "部门"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # 数据行
    for i, row in enumerate(result.rows, 4):
        ws.cell(row=i, column=1, value=row.seq)
        ws.cell(row=i, column=2, value=row.area)
        ws.cell(row=i, column=3, value=row.store)
        ws.cell(row=i, column=4, value=row.name)
        ws.cell(row=i, column=5, value=row.employee_id)
        c = ws.cell(row=i, column=6, value=row.sales_amount)
        c.number_format = '#,##0.00'
        c.alignment = Alignment(horizontal='right')
        p = ws.cell(row=i, column=7, value=f"{row.percentage:.2f}%")
        p.alignment = Alignment(horizontal='right')
        ws.cell(row=i, column=8, value=row.department)
    
    # 合计行
    total_row = len(result.rows) + 4
    ws.cell(row=total_row, column=1, value="合计")
    ws.cell(row=total_row, column=1).font = Font(bold=True)
    c = ws.cell(row=total_row, column=6, value=result.total_row.total_sales)
    c.number_format = '#,##0.00'
    c.font = Font(bold=True)
    
    wb.save(filepath)
```

### 2.6 Pipeline 模块（src/pipeline.py）

**职责**: 全流程编排（导出 → 分析 → 报告）。

```python
def run_full_pipeline(
    config_path: str,
    template_name: str,
) -> AnalysisReport:
    """
    一键执行全流程：
    1. 加载导出配置
    2. 连接 SQL Server 并导出数据 → ExportResult
    3. 加载分析模版
    4. 执行模版分析 → AnalysisResult
    5. 生成报告 → AnalysisReport
    6. 记录日志和元数据
    """
    log = structlog.get_logger()
    
    # Step 1: Export
    log.info("export.start", config=config_path)
    export_config = load_export_config(config_path)
    export_result = execute_export(export_config)
    log.info("export.done", rows=export_result.row_count, elapsed=export_result.elapsed_seconds)
    
    # Step 2: Analyze
    log.info("analysis.start", template=template_name)
    template = TemplateRegistry().get(template_name)
    raw_data = pd.read_excel(export_result.file_path)
    analysis_result = run_analysis(template, raw_data, export_config)
    log.info("analysis.done", matched=analysis_result.metadata.matched_rows, total=analysis_result.total_row.total_sales)
    
    # Step 3: Report
    log.info("report.start")
    report = generate_reports(analysis_result, export_config.parameters)
    log.info("report.done", markdown=report.markdown_path, excel=report.excel_path)
    
    return report
```

### 2.7 CLI 模块（src/cli.py）

**命令结构**:
```
ai-export
├── run              # 一键执行全流程
│   --template       # 指定模版名称（必填）
│   --config         # 导出配置文件路径（默认 configs/export.yaml）
│   --date-start     # 覆盖开始日期
│   --date-end       # 覆盖结束日期
├── export           # 仅导出数据
│   --config         # 配置文件路径
├── analyze          # 仅执行分析
│   --template       # 模版名称
│   --data           # 数据文件路径
├── list-templates   # 列出所有可用模版
└── validate         # 校验所有配置文件
```

**命令输出示例**:
```
$ ai-export run --template sanzhen-jiuti

🔄 [导出] 连接 SQL Server (192.168.1.100:1433)...
✅ [导出] 查询完成: 2345 行, 耗时 2.3s
   → output/exports/export_20260622_113000.xlsx

🔄 [分析] 匹配模版 "三诊九体培训动销及打卡学习情况"
✅ [分析] 匹配 61/61 员工
   ✅ 有销售: 48 人, 销售金额 ¥37,326.00
   ⚠️ 无销售: 13 人
   📊 连锁月度总销售额: ¥76,788.68
   📊 占比: 48.61%

🔄 [报告] 生成报告...
✅ [报告] output/reports/report_sanzhen_20260622_113000.md
✅ [报告] output/reports/report_sanzhen_20260622_113000.xlsx

🎉 全流程完成，耗时 5.8s
```

## 3. 接口定义

### 3.1 公共 API

```python
# src/config/loader.py
def load_export_config(path: str) -> ExportConfig: ...
def load_template(path: str) -> AnalysisTemplate: ...

# src/config/validator.py
def validate_export_config(config: ExportConfig) -> None: ...
def validate_template(template: AnalysisTemplate) -> None: ...

# src/export/connector.py
class SQLServerConnector: ...
def get_connection(config: ExportConfig) -> SQLServerConnector: ...

# src/export/executor.py
def execute_query(connector, query: str, params: dict) -> pd.DataFrame: ...
def export_to_excel(df: pd.DataFrame, config: ExportConfig) -> ExportResult: ...

# src/analysis/engine.py
def run_analysis(template: AnalysisTemplate, data: pd.DataFrame, config: ExportConfig) -> AnalysisResult: ...

# src/report/markdown.py
def generate_markdown_report(result: AnalysisResult, output_dir: str) -> str: ...

# src/report/excel.py
def generate_excel_report(result: AnalysisResult, output_dir: str) -> str: ...

# src/pipeline.py
def run_full_pipeline(config_path: str, template_name: str) -> AnalysisReport: ...
```

## 4. 错误处理策略

```
┌──────────────────┬──────────────────────────────┬──────────────┐
│ 错误类型          │ 处理方式                      │ 用户可见      │
├──────────────────┼──────────────────────────────┼──────────────┤
│ 配置文件不存在    │ FileNotFoundError              │ "配置文件未找到: path" │
│ 配置格式错误      │ ConfigValidationError          │ "字段 'server' 为必填" │
│ SQL连接失败       │ ConnectionError               │ "无法连接 SQL Server (host:port)" │
│ SQL执行失败       │ QueryExecutionError           │ "查询执行失败: 语法错误" │
│ SQL超时          │ TimeoutError                  │ "查询超时 (>30s)" │
│ 模版不存在        │ TemplateNotFoundError         │ "模版 'xxx' 未注册" │
│ 数据文件不存在    │ FileNotFoundError              │ "数据文件未找到: path" │
│ 数据为空          │ EmptyDataWarning (log)        │ (日志记录，正常完成) │
│ 匹配率为0         │ NoMatchWarning (log)          │ "警告: 所有员工均未匹配" │
│ 未知错误          │ 完整 traceback 记录日志         │ "发生未知错误，详见日志" │
└──────────────────┴──────────────────────────────┴──────────────┘
```

## 5. 日志规范

使用 structlog 结构化日志：

```python
# 关键事件日志点
log.info("pipeline.start", template="sanzhen-jiuti", date="2026-06-01..2026-06-16")
log.info("export.connecting", server="...", port=1433, database="...")
log.info("export.complete", row_count=2345, elapsed=2.3)
log.info("analysis.matching", template_rows=61)
log.info("analysis.match_result", matched=48, not_matched=13, unmatched_data=5, match_rate=0.79)
log.info("analysis.calculation", total_sales=76788.68, employee_total=37326.00, ratio=0.4861)
log.info("report.generated", markdown="path/to/report.md", excel="path/to/report.xlsx")
log.error("export.connection_failed", server="...", error="Connection refused")
```

## 6. 配置示例

### export.yaml（完整示例）

已在上方 quickstart 中包含，参考 [quickstart.md](quickstart.md)。

### 模版格式规范

```yaml
# 模版必需字段
name: str              # 唯一标识符，用于 --template 参数
display_name: str       # 报告中显示的标题
columns: list[Column]   # 列定义
group_by: list[str]     # 分组维度
match_key: MatchKey     # 匹配策略
employee_list: list[Employee]  # 预定义员工列表

# 模版可选字段
description: str        # 模版描述
sort_by: list[SortRule] # 排序规则（默认按 employee_list 顺序）
summary_rules: list[SummaryRule]  # 汇总规则
```
