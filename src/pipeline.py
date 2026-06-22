"""Full pipeline orchestration: export → analyze → report."""

import calendar
import time
from datetime import datetime, date, timedelta

import pandas as pd
import structlog

from src.config.loader import load_export_config
from src.config.models import AnalysisReport, ExportResult
from src.export.executor import execute_export
from src.analysis.engine import run_analysis
from src.report.markdown import generate_markdown_report
from src.report.excel import generate_excel_report
from src.template.registry import TemplateRegistry

log = structlog.get_logger()


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""


def get_auto_date_range(today: date | None = None) -> tuple[str, str]:
    """Calculate date range based on today's date for scheduled exports.

    Rules:
    - On the 16th of the month: 1st → 16th of current month
    - On the 1st of the month: 1st of last month → 1st of current month

    Args:
        today: Override for testing (defaults to date.today()).

    Returns:
        (start_date, end_date) as YYYY-MM-DD strings.
    """
    t = today or date.today()

    if t.day == 16:
        start = date(t.year, t.month, 1)
        end = date(t.year, t.month, 16)
        log.info("schedule.mid_month", range=f"{start} ~ {end}")
    elif t.day == 1:
        # First of the month → previous full month
        if t.month == 1:
            prev_month = 12
            prev_year = t.year - 1
        else:
            prev_month = t.month - 1
            prev_year = t.year
        start = date(prev_year, prev_month, 1)
        end = date(t.year, t.month, 1)  # 1st of current month (exclusive)
        log.info("schedule.beginning_of_month", range=f"{start} ~ {end}")
    else:
        # Default fallback: current month up to today
        start = date(t.year, t.month, 1)
        end = t
        log.info("schedule.default", range=f"{start} ~ {end}")

    return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))


def run_full_pipeline(
    config_path: str,
    template_name: str,
    date_start: str | None = None,
    date_end: str | None = None,
    auto_date: bool = False,
) -> AnalysisReport:
    """Execute the complete AIExport pipeline.

    Stages:
      1. Load export configuration.
      2. Connect to SQL Server and export data → .xlsx.
      3. Load analysis template.
      4. Match, aggregate, and calculate percentages.
      5. Generate Markdown + Excel reports.

    Args:
        config_path: Path to export.yaml.
        template_name: Template name registered in configs/templates/.
        date_start: Optional date range override (start).
        date_end: Optional date range override (end).

    Returns:
        AnalysisReport with paths to generated files.
    """
    pipeline_start = time.time()
    log.info("pipeline.start", config=config_path, template=template_name)

    # ── Stage 1: Load config + override dates ──
    config = load_export_config(config_path)
    if auto_date:
        auto_start, auto_end = get_auto_date_range()
        config.parameters["start_date"] = auto_start
        config.parameters["end_date"] = auto_end
        log.info("pipeline.auto_date", start=auto_start, end=auto_end)
    if date_start:
        config.parameters["start_date"] = date_start
    if date_end:
        config.parameters["end_date"] = date_end

    # ── Stage 2: Export ──
    log.info("pipeline.stage", stage="export")
    try:
        export_result = execute_export(config)
        if export_result.error:
            raise PipelineError(f"导出失败: {export_result.error}")
    except Exception as e:
        raise PipelineError(f"导出阶段失败: {e}") from e

    print(f"[OK] [导出] 完成: {export_result.row_count} 行, 耗时 {export_result.elapsed_seconds}s")
    print(f"   → {export_result.file_path}")

    # ── Stage 3: Load template ──
    log.info("pipeline.stage", stage="analyze")
    registry = TemplateRegistry("configs/templates")
    template = registry.get(template_name)

    # ── Stage 4: Load data and analyze ──
    data = pd.read_excel(export_result.file_path)
    analysis_result = run_analysis(template, data, config)

    matched_count = analysis_result.metadata.matched_rows
    not_matched = analysis_result.metadata.unmatched_rows
    total = analysis_result.total_row.total_sales
    print(f"[OK] [分析] 完成: 匹配 {matched_count}/{len(template.employee_list)} 员工")
    if not_matched > 0:
        print(f"   [WARN] {not_matched} 名模版员工无销售记录")
    print(f"   [DATA] 合计销售额: ¥{total:,.2f}")

    # ── Stage 5: Report ──
    log.info("pipeline.stage", stage="report")
    md_path = generate_markdown_report(
        analysis_result,
        output_dir="output/reports",
        display_name=template.display_name,
        chain_total=analysis_result.chain_total,
    )
    xlsx_path = generate_excel_report(
        analysis_result,
        output_dir="output/reports",
        display_name=template.display_name,
        chain_total=analysis_result.chain_total,
    )

    print(f"[OK] [报告] 已生成:")
    print(f"   → {md_path}")
    print(f"   → {xlsx_path}")

    elapsed = time.time() - pipeline_start
    log.info("pipeline.complete", elapsed=round(elapsed, 2))
    print(f"\n[DONE] 全流程完成，耗时 {elapsed:.1f}s")

    return AnalysisReport(
        markdown_path=md_path,
        excel_path=xlsx_path,
        generated_at=datetime.now(),
        template_name=template_name,
        date_range=(
            config.parameters.get("start_date", ""),
            config.parameters.get("end_date", ""),
        ),
    )
