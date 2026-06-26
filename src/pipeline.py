"""Full pipeline orchestration: export → analyze → report."""

import os
import time
import structlog
from datetime import datetime, date, timedelta

import pandas as pd

from src.config.loader import load_export_config
from src.config.models import (
    AnalysisReport,
    QueryGroupConfig,
    PipelineResult,
)
from src.export.executor import execute_export
from src.analysis.engine import run_analysis
from src.report.excel import generate_excel_report

log = structlog.get_logger()


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""


# ── Date helpers ──


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
        if t.month == 1:
            prev_month = 12
            prev_year = t.year - 1
        else:
            prev_month = t.month - 1
            prev_year = t.year
        start = date(prev_year, prev_month, 1)
        end = date(t.year, t.month, 1)
        log.info("schedule.beginning_of_month", range=f"{start} ~ {end}")
    else:
        start = date(t.year, t.month, 1)
        end = t
        log.info("schedule.default", range=f"{start} ~ {end}")

    return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))


def _adjust_end_date_for_display(raw_end: str) -> str:
    """Subtract 1 day from end_date for display (SQL uses < end_date exclusive)."""
    try:
        end_dt = datetime.strptime(raw_end, "%Y-%m-%d") - timedelta(days=1)
        return end_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return raw_end


# ── Single query group execution ──


def _run_single_group(
    config,
    qg: QueryGroupConfig,
    output_dir: str = "output/reports",
    generate_charts: bool = True,
    generate_pdf: bool = True,
) -> AnalysisReport:
    """Execute pipeline stages for a single query group.

    Returns an AnalysisReport with all generated file paths.
    """
    # ── Stage 1: Export ──
    log.info("pipeline.stage", stage="export", group=qg.name)
    export_result = execute_export(config, qg)
    if export_result.error:
        raise PipelineError(f"[{qg.name}] 导出失败: {export_result.error}")

    print(f"[OK] [{qg.name}] 导出: {export_result.row_count} 行, 耗时 {export_result.elapsed_seconds}s")
    print(f"   → {export_result.file_path}")

    # ── Create per-file subdirectory (matches analyze-file naming) ──
    export_stem = os.path.splitext(os.path.basename(export_result.file_path))[0]
    group_output_dir = os.path.join(output_dir, export_stem)
    # Clean up previous reports before regenerating
    import shutil
    if os.path.isdir(group_output_dir):
        shutil.rmtree(group_output_dir)

    # ── Stage 2: Load data ──
    data = pd.read_excel(export_result.file_path)
    if data.empty:
        print(f"[WARN] [{qg.name}] 导出数据为空，跳过分析")
        return AnalysisReport(template_name=qg.name)

    # ── Stage 3: Auto-generate template from data ──
    if not qg.analyze:
        print(f"[OK] [{qg.name}] analyze=false，跳过分析和报告")
        return AnalysisReport(template_name=qg.name, markdown_path=export_result.file_path)
    if not qg.template:
        print(f"[OK] [{qg.name}] 无 template 配置，跳过分析和报告")
        return AnalysisReport(template_name=qg.name, markdown_path=export_result.file_path)

    from src.template.auto import auto_generate_template
    template = auto_generate_template(data, qg.name, qg.template)
    log.info("pipeline.auto_template", group=qg.name, employees=len(template.employee_list))

    # ── Stage 4: Analysis ──
    log.info("pipeline.stage", stage="analyze", group=qg.name)
    analysis_result = run_analysis(
        template, data, config,
        summary_value=export_result.summary_value,
    )

    matched = analysis_result.metadata.matched_rows
    not_matched = analysis_result.metadata.unmatched_rows
    total = analysis_result.total_row.total_sales

    print(f"[OK] [{qg.name}] 分析: 匹配 {matched}/{len(template.employee_list)}")
    if not_matched > 0:
        print(f"   [WARN] {not_matched} 条未匹配")
    print(f"   [DATA] 合计销售额: ¥{total:,.2f}")

    # ── Stage 5: Charts ──
    chart_paths: list[str] = []
    if generate_charts:
        try:
            from src.chart.generator import generate_charts_for_analysis
            chart_paths = generate_charts_for_analysis(analysis_result, output_dir=group_output_dir)
            if chart_paths:
                print(f"[OK] [{qg.name}] 图表: {len(chart_paths)} 张")
        except Exception as e:
            log.warning("pipeline.chart_failed", group=qg.name, error=str(e))

    # ── Stage 6: Reports ──
    log.info("pipeline.stage", stage="report", group=qg.name)
    display_name = qg.template.display_name if qg.template else qg.name
    chain_total = analysis_result.chain_total

    xlsx_path = generate_excel_report(
        analysis_result,
        output_dir=group_output_dir,
        display_name=display_name,
        chain_total=chain_total,
    )

    pdf_path = ""
    if generate_pdf:
        try:
            from src.report.pdf import generate_pdf_report
            pdf_path = generate_pdf_report(
                analysis_result,
                output_dir=group_output_dir,
                display_name=display_name,
                chain_total=chain_total,
                chart_paths=chart_paths,
            )
        except Exception as e:
            log.warning("pipeline.pdf_failed", group=qg.name, error=str(e))

    # Determine display date range
    raw_start = qg.parameters.get("start_date", "")
    raw_end = qg.parameters.get("end_date", "")
    display_end = _adjust_end_date_for_display(raw_end)

    return AnalysisReport(
        excel_path=xlsx_path,
        pdf_path=pdf_path,
        chart_paths=chart_paths,
        template_name=qg.name,
        date_range=(raw_start, display_end),
        markdown_path=export_result.file_path,  # reuse field for export path
    )


# ── Main entry point ──


def run_full_pipeline(
    config_path: str,
    date_start: str | None = None,
    date_end: str | None = None,
    auto_date: bool = False,
    query_group_filter: str | None = None,
    generate_charts: bool = True,
    generate_pdf: bool = True,
) -> PipelineResult:
    """Execute the complete AIExport pipeline.

    Reads export.yaml with a queries: block of named query groups.
    Each group has inline template config — no external YAML templates needed.
    Templates are auto-generated from SQL query results.

    Args:
        config_path: Path to export.yaml.
        date_start / date_end: Date range overrides.
        auto_date: Use auto-calculated date range.
        query_group_filter: Run only this query group.
        generate_charts: Whether to generate chart PNGs.
        generate_pdf: Whether to generate PDF reports.

    Returns:
        PipelineResult with all generated report paths.
    """
    pipeline_start = time.time()
    log.info("pipeline.start", config=config_path)

    # ── Load config ──
    config = load_export_config(config_path)

    if not config.queries:
        raise PipelineError(
            "export.yaml 缺少 queries: 配置块。\n"
            "请在 export.yaml 中定义 queries: 块，每个查询组需包含 detail_query + template 内联模版。"
        )

    # ── Resolve dates ──
    if auto_date:
        auto_start, auto_end = get_auto_date_range()
        config.parameters["start_date"] = auto_start
        config.parameters["end_date"] = auto_end
        log.info("pipeline.auto_date", start=auto_start, end=auto_end)
    if date_start:
        config.parameters["start_date"] = date_start
    if date_end:
        config.parameters["end_date"] = date_end

    # ── Filter query groups ──
    query_groups = config.queries
    if query_group_filter:
        if query_group_filter not in query_groups:
            raise PipelineError(
                f"查询组 '{query_group_filter}' 未找到。"
                f"可用: {', '.join(query_groups.keys())}"
            )
        query_groups = {query_group_filter: query_groups[query_group_filter]}

    reports: list[AnalysisReport] = []
    errors: list[str] = []
    executed = 0
    failed = 0
    output_dir = config.output_dir.replace("exports", "reports")
    # Clean up old report directories and old exports from previous runs
    import shutil as _shutil
    if os.path.isdir(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isdir(item_path):
                _shutil.rmtree(item_path)
    exports_dir = config.output_dir
    if os.path.isdir(exports_dir):
        for item in os.listdir(exports_dir):
            item_path = os.path.join(exports_dir, item)
            if os.path.isfile(item_path) and item.endswith(('.xlsx', '.xls')):
                os.remove(item_path)
    exported_by_pipeline: set[str] = set()  # ALL files exported by this run

    for name, qg in query_groups.items():
        # Apply date overrides to each group's parameters
        if date_start:
            qg.parameters["start_date"] = date_start
        if date_end:
            qg.parameters["end_date"] = date_end
        if auto_date:
            qg.parameters["start_date"] = config.parameters.get("start_date", "")
            qg.parameters["end_date"] = config.parameters.get("end_date", "")

        print(f"\n{'='*50}")
        print(f"[GROUP] {name}")
        print(f"{'='*50}")

        # Sync query group parameters to root config for analysis (date_range etc.)
        config.parameters.update(qg.parameters)

        try:
            report = _run_single_group(
                config, qg,
                output_dir=output_dir,
                generate_charts=generate_charts,
                generate_pdf=generate_pdf,
            )
            reports.append(report)
            executed += 1
            # Track pipeline-exported files via the export path
            export_path = report.markdown_path or report.excel_path
            if export_path and os.path.isfile(export_path):
                exported_by_pipeline.add(os.path.abspath(export_path))
        except Exception as e:
            failed += 1
            errors.append(f"[{name}] {e}")
            log.error("pipeline.group_failed", group=name, error=str(e))
            print(f"[FAIL] [{name}] {e}")

    # ── File analysis phase: only analyze files created during this run ──
    exports_dir = config.output_dir
    import glob as _glob
    file_results: list = []
    if os.path.isdir(exports_dir):
        supported_exts = ["*.xlsx", "*.xls", "*.csv"]
        exported_files: list[str] = []
        for ext in supported_exts:
            exported_files.extend(_glob.glob(os.path.join(exports_dir, ext)))
        exported_files.sort()

        # Only external files created since pipeline start (not old files)
        exported_files = [f for f in exported_files if os.path.getmtime(f) >= pipeline_start]
        # Skip files from pipeline query groups (already have Phase 1 reports)
        exported_files = [f for f in exported_files if os.path.abspath(f) not in exported_by_pipeline]

        if exported_files:
            print(f"\n{'='*50}")
            print(f"[PHASE] 文件分析 — {len(exported_files)} 个文件")
            print(f"{'='*50}")

            from src.pipeline_file import run_file_analysis
            for fpath in exported_files:
                fname = os.path.basename(fpath)
                print(f"\n[FILE] {fname}")
                try:
                    fr = run_file_analysis(
                        file_path=fpath,
                        output_dir=output_dir,
                        generate_charts=generate_charts,
                        generate_pdf=generate_pdf,
                    )
                    file_results.append(fr)
                    if fr.error:
                        print(f"   [WARN] {fr.error}")
                except Exception as e:
                    log.error("pipeline.file_analysis_failed", file=fpath, error=str(e))
                    print(f"   [ERR] {e}")

    elapsed = time.time() - pipeline_start
    print(f"\n{'='*50}")
    print(f"[DONE] 完成 {executed}/{executed + failed} 个查询组 + {len(file_results)} 个文件分析, 耗时 {elapsed:.1f}s")
    for err in errors:
        print(f"   [ERR] {err}")

    return PipelineResult(
        reports=reports,
        total_elapsed=round(elapsed, 2),
        query_groups_executed=executed,
        query_groups_failed=failed,
        errors=errors,
    )
