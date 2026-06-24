"""Analysis engine — orchestrates matching, calculation, and result assembly."""

import time
from datetime import datetime

import pandas as pd
import structlog

from src.analysis.calculator import calculate_percentages, calculate_total
from src.analysis.matcher import match_employees
from src.config.models import (
    AnalysisMetadata,
    AnalysisResult,
    AnalysisTemplate,
    ExportConfig,
)
from src.export.connector import SQLServerConnector
from src.export.executor import _resolve_query

log = structlog.get_logger()


def run_analysis(
    template: AnalysisTemplate,
    data: pd.DataFrame,
    config: ExportConfig,
    total_sales_override: float | None = None,
    summary_value: float | None = None,
) -> AnalysisResult:
    """Run the full analysis pipeline on exported data.

    1. Match template employees to data rows.
    2. Calculate percentages against total sales.
    3. Compute totals.
    4. Assemble and return AnalysisResult.

    Args:
        template: The analysis template to apply.
        data: Raw export data as a pandas DataFrame.
        config: ExportConfig (used to resolve parameters for summary query).
        total_sales_override: If provided, skip the summary query and use this value.
        summary_value: Pre-executed summary query result (avoids re-connecting).

    Returns:
        Fully populated AnalysisResult.
    """
    start = time.time()

    # Step 1: Match
    log.info("analysis.matching", template=template.name)
    matched_rows, unmatched_rows = match_employees(template, data)

    # Step 2: Get total sales for percentage calculation
    total_sales: float = total_sales_override or summary_value or 0.0
    if total_sales == 0.0 and config.summary_query:
        try:
            with SQLServerConnector(config) as db:
                summary_sql = _resolve_query(config.summary_query, config.parameters)
                db.execute(summary_sql)
                total_sales = db.fetch_value()
                log.info("analysis.total_sales", total_sales=total_sales)
        except Exception as e:
            log.warning("analysis.summary_query_failed", error=str(e))
            # Fallback: use sum of all employee sales
            total_sales = sum(r.sales_amount for r in matched_rows)

    # Step 3: Calculate percentages
    matched_rows = calculate_percentages(matched_rows, total_sales)

    # Step 4: Calculate totals
    total_row = calculate_total(matched_rows)

    elapsed = time.time() - start

    # Step 5: Assemble metadata
    # Adjust end_date for display: SQL uses < end_date (exclusive),
    # so actual data ends on end_date - 1 day.
    raw_start = config.parameters.get("start_date", "")
    raw_end = config.parameters.get("end_date", "")
    try:
        from datetime import timedelta
        end_dt = datetime.strptime(raw_end, "%Y-%m-%d") - timedelta(days=1)
        display_end = end_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        display_end = raw_end

    metadata = AnalysisMetadata(
        raw_data_rows=len(data),
        template_rows=len(template.employee_list),
        matched_rows=sum(1 for r in matched_rows if r.matched),
        unmatched_rows=sum(1 for r in matched_rows if not r.matched),
        match_rate=(sum(1 for r in matched_rows if r.matched) / len(template.employee_list))
            if template.employee_list else 0.0,
        elapsed_seconds=round(elapsed, 2),
        date_range=(raw_start, display_end),
    )

    log.info(
        "analysis.complete",
        matched=metadata.matched_rows,
        total_sales=total_row.total_sales,
        elapsed=elapsed,
    )

    return AnalysisResult(
        template_name=template.name,
        executed_at=datetime.now(),
        rows=matched_rows,
        unmatched_rows=unmatched_rows,
        total_row=total_row,
        metadata=metadata,
        chain_total=total_sales,
    )
