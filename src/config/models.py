"""Data models for configuration entities."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExportConfig:
    """SQL Server export configuration."""
    # Connection
    server: str
    database: str
    username: str
    password: str = ""
    port: int = 1433

    # Queries (optional when queries: block is present)
    detail_query: str = ""
    summary_query: str = ""

    # Parameters for {{placeholder}} substitution
    parameters: dict = field(default_factory=dict)

    # Output
    output_dir: str = "output/exports"
    output_filename: str = "export_result.xlsx"

    # Timeout in seconds
    timeout: int = 30

    # Multi-query mode: named query groups
    queries: dict = field(default_factory=dict)  # dict[str, QueryGroupConfig]


@dataclass
class TemplateColumn:
    """Column definition in an analysis template."""
    title: str
    source_field: str
    format: str = "text"   # text | number | money | percent
    width: int = 15


@dataclass
class SortRule:
    """Sorting rule."""
    field: str
    order: str = "asc"     # asc | desc


@dataclass
class MatchKey:
    """Defines how to match template rows to data rows."""
    template_fields: list[str] = field(default_factory=list)
    data_fields: list[str] = field(default_factory=list)


@dataclass
class SummaryRule:
    """Aggregation rule definition."""
    type: str              # sum | count | avg | percentage
    source_field: str
    target_field: str
    base_field: str = ""   # required when type='percentage'


@dataclass
class TemplateInlineConfig:
    """Inline template specification from export.yaml queries[].template."""
    group_by: list[str] = field(default_factory=list)
    match_key: MatchKey = field(default_factory=MatchKey)
    sort_by: list[SortRule] = field(default_factory=list)
    display_name: str = ""
    value_field: str = ""  # numeric sales column (auto-detect if empty)


@dataclass
class QueryGroupConfig:
    """A single named query group within export.yaml queries{} block.

    Connection fields (server, database, etc.) are optional — when empty,
    the root-level ExportConfig values are used as defaults.
    """
    name: str
    detail_query: str
    summary_query: str = ""
    parameters: dict = field(default_factory=dict)
    output_filename: str = ""
    template: TemplateInlineConfig | None = None
    # Per-group connection overrides (empty = use root-level defaults)
    server: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    timeout: int = 0


@dataclass
class EmployeeRow:
    """Pre-defined or auto-generated employee row in a template."""
    seq: int
    area: str = ""
    store: str = ""
    name: str = ""
    employee_id: str = ""
    department: str = ""


@dataclass
class AnalysisTemplate:
    """Full analysis template definition."""
    name: str
    display_name: str
    description: str = ""
    columns: list[TemplateColumn] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    sort_by: list[SortRule] = field(default_factory=list)
    match_key: MatchKey = field(default_factory=MatchKey)
    summary_rules: list[SummaryRule] = field(default_factory=list)
    employee_list: list[EmployeeRow] = field(default_factory=list)
    value_field: str = ""  # which data column holds the sales value


# ── Runtime result models ──


@dataclass
class ExportResult:
    """Result of a data export operation."""
    config_name: str
    executed_at: datetime = field(default_factory=datetime.now)
    row_count: int = 0
    columns: list[str] = field(default_factory=list)
    file_path: str = ""
    elapsed_seconds: float = 0.0
    error: str | None = None
    query_group_name: str = ""     # which query group produced this
    summary_value: float = 0.0     # cached summary query result


@dataclass
class AnalysisRow:
    """A single row in the analysis result table."""
    seq: int
    area: str
    store: str
    name: str
    employee_id: str
    sales_amount: float = 0.0
    percentage: float = 0.0
    department: str = ""
    matched: bool = True


@dataclass
class AnalysisTotal:
    """Totals row."""
    total_sales: float = 0.0
    total_employees: int = 0
    total_stores: int = 0
    total_percentage: float = 100.0


@dataclass
class AnalysisMetadata:
    """Analysis run metadata."""
    raw_data_rows: int = 0
    template_rows: int = 0
    matched_rows: int = 0
    unmatched_rows: int = 0
    match_rate: float = 0.0
    elapsed_seconds: float = 0.0
    date_range: tuple = ()


@dataclass
class AnalysisResult:
    """Full analysis result."""
    template_name: str = ""
    executed_at: datetime = field(default_factory=datetime.now)
    rows: list[AnalysisRow] = field(default_factory=list)
    unmatched_rows: list[dict] = field(default_factory=list)
    total_row: AnalysisTotal = field(default_factory=AnalysisTotal)
    metadata: AnalysisMetadata = field(default_factory=AnalysisMetadata)
    chain_total: float = 0.0  # From summary query — chain-wide total sales


@dataclass
class AnalysisReport:
    """Generated report paths."""
    markdown_path: str = ""
    excel_path: str = ""
    pdf_path: str = ""
    chart_paths: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    template_name: str = ""
    date_range: tuple = ()


@dataclass
class PipelineResult:
    """Overall result of a pipeline run (may contain multiple reports)."""
    reports: list[AnalysisReport] = field(default_factory=list)
    total_elapsed: float = 0.0
    query_groups_executed: int = 0
    query_groups_failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FileAnalysisResult:
    """Result of a file analysis run (no template, no employee matching).

    Used by the analyze-file command for arbitrary .xlsx/.xls/.csv files.
    """
    file_path: str = ""
    file_label: str = ""        # stem of the filename
    file_type: str = ""         # xlsx, xls, or csv
    excel_path: str = ""
    pdf_path: str = ""
    chart_paths: list[str] = field(default_factory=list)
    row_count: int = 0
    col_count: int = 0
    value_col: str = ""
    name_col: str = ""
    group_col: str = ""
    total_value: float = 0.0
    error: str = ""
