# Phase 1 Data Model: AIExport

**Feature**: AI 导出与分析系统
**Date**: 2026-06-22

## Entity Definitions

### 1. ExportConfig（导出配置）

```python
@dataclass
class ExportConfig:
    """SQL Server 导出配置"""
    # 连接参数
    server: str                    # 服务器地址，如 "192.168.1.100"
    port: int = 1433              # 端口，默认 1433
    database: str                  # 数据库名称
    username: str                  # 用户名
    password: str                  # 密码（或环境变量引用）
    
    # 查询定义
    detail_query: str             # 明细查询 SQL（支持 {{param}} 占位符）
    summary_query: str            # 汇总查询 SQL（计算总销售额）
    
    # 参数
    parameters: dict[str, str]    # 查询参数，如 {"start_date": "2026-06-01", ...}
    
    # 输出
    output_dir: str = "output/exports"  # 导出文件目录
    output_filename: str = "export_result.xlsx"
    
    # 连接超时
    timeout: int = 30              # 秒
```

**Validation Rules**:
- `server`, `database`, `username`, `detail_query` 必填
- `port` 范围: 1–65535
- `timeout` 范围: 5–300

### 2. AnalysisTemplate（分析模版）

```python
@dataclass
class AnalysisTemplate:
    """分析模版定义"""
    name: str                          # 模版名称（唯一标识）
    display_name: str                  # 显示名称
    description: str = ""              # 模版描述
    
    columns: list[TemplateColumn]      # 列定义
    group_by: list[str]                # 分组维度，如 ["片区", "门店", "员工ID"]
    sort_by: list[SortRule]            # 排序规则
    match_key: MatchKey                # 匹配策略
    summary_rules: list[SummaryRule]   # 汇总规则
    
    employee_list: list[EmployeeRow]   # 预定义员工列表（模版行）


@dataclass
class TemplateColumn:
    """模版列定义"""
    title: str                         # 列显示名，如 "序号"
    source_field: str                  # 数据来源字段，如 "销售店员姓名"
    format: str = "text"              # 格式化: text|number|money|percent
    width: int = 15                    # 列宽（Excel）


@dataclass
class SortRule:
    """排序规则"""
    field: str                         # 排序字段
    order: str = "asc"                # asc|desc
    custom_order: list[str] = None    # 自定义顺序（如片区优先级）


@dataclass
class MatchKey:
    """匹配键定义"""
    template_fields: list[str]        # 模版中用于匹配的字段
    data_fields: list[str]            # 数据中用于匹配的字段
    
    # 示例: template_fields=["员工ID", "门店"], data_fields=["销售店员ERPID", "销售门店"]


@dataclass
class SummaryRule:
    """汇总规则"""
    type: str                          # sum|count|avg|percentage
    source_field: str                  # 源字段
    target_field: str                  # 目标字段名
    base_field: str = None            # 占比计算的基数（percentage 类型必填）


@dataclass
class EmployeeRow:
    """模版中预定义的员工行"""
    seq: int                           # 序号
    area: str                          # 片区
    store: str                         # 门店
    name: str                          # 姓名
    employee_id: str                   # 第三方员工ID
    department: str                    # 部门
```

**Validation Rules**:
- `name` 必须是唯一的模版标识
- `columns` 至少包含 1 个列定义
- `group_by` 至少包含 1 个分组维度
- `match_key.template_fields` 和 `match_key.data_fields` 长度必须相等
- `employee_list` 至少包含 1 个员工

### 3. ExportResult（导出结果）

```python
@dataclass
class ExportResult:
    """数据导出结果"""
    config_name: str                   # 使用的导出配置名
    executed_at: datetime              # 执行时间戳
    row_count: int                     # 导出行数
    columns: list[str]                 # 列名列表
    file_path: str                     # 导出文件路径
    elapsed_seconds: float             # 查询耗时
    error: str | None = None          # 错误信息（成功时为 None）
```

### 4. AnalysisResult（分析结果）

```python
@dataclass
class AnalysisResult:
    """模版分析结果"""
    template_name: str                 # 使用的模版名称
    executed_at: datetime              # 执行时间
    
    rows: list[AnalysisRow]            # 匹配成功的行（按模版顺序）
    unmatched_rows: list[dict]         # 数据中未匹配模版的行
    
    total_row: AnalysisTotal           # 合计行
    
    metadata: AnalysisMetadata         # 分析元数据


@dataclass
class AnalysisRow:
    """分析结果中的一行"""
    seq: int                           # 序号
    area: str                          # 片区
    store: str                         # 门店
    name: str                          # 姓名
    employee_id: str                   # 第三方员工ID
    sales_amount: float                # 销售金额
    percentage: float                  # 销售占比（0.0–100.0）
    department: str                    # 部门
    matched: bool = True               # 是否匹配到数据


@dataclass
class AnalysisTotal:
    """合计行"""
    total_sales: float                 # 总销售额
    total_employees: int               # 总员工数（有销售记录的）
    total_stores: int                  # 总门店数
    total_percentage: float = 100.0    # 总占比


@dataclass
class AnalysisMetadata:
    """分析元数据"""
    raw_data_rows: int                 # 原始数据行数
    template_rows: int                 # 模版定义行数
    matched_rows: int                  # 匹配成功行数
    unmatched_rows: int                # 未匹配行数
    match_rate: float                  # 匹配率（matched / template_rows）
    elapsed_seconds: float             # 分析耗时
    date_range: tuple[str, str]        # 分析日期范围
```

### 5. AnalysisReport（分析报告）

```python
@dataclass
class AnalysisReport:
    """分析报告"""
    markdown_path: str                 # Markdown 报告路径
    excel_path: str                    # Excel 报告路径
    generated_at: datetime             # 生成时间
    template_name: str                 # 模版名称
    date_range: tuple[str, str]        # 日期范围
```

## Entity Relationships

```
ExportConfig ──1:N──▶ ExportResult
     │
     │ (provides data to)
     ▼
AnalysisTemplate ──1:1──▶ AnalysisResult
     │                        │
     │                        │ (feeds into)
     │                        ▼
     └──────────────▶ AnalysisReport
```

## State Transitions

```
ExportConfig:  [validated] ──▶ [executing] ──▶ [completed|failed]
                                                      │
AnalysisTemplate: [validated] ──▶ [matching] ──▶ [calculating] ──▶ [completed]
                                                                     │
AnalysisReport: [generating] ──▶ [completed]
```
