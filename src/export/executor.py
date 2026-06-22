"""Query execution and data export orchestrator."""

import re
import time
from datetime import datetime

import pandas as pd
import structlog

from src.config.models import ExportConfig, ExportResult
from src.export.connector import ConnectionError, SQLServerConnector

log = structlog.get_logger()


def _resolve_query(query: str, params: dict[str, str]) -> str:
    """Replace {{param}} placeholders with actual values from params dict.

    This performs template-level parameter substitution BEFORE the query
    is sent to the database. The parameters are trusted admin-provided
    values (dates, IDs in IN clauses), not end-user input.
    """
    def _replace(match):
        key = match.group(1).strip()
        if key not in params:
            log.warning("query.missing_param", param=key)
            return match.group(0)
        return params[key]

    return re.sub(r"\{\{(\w+)\}\}", _replace, query)


def execute_export(config: ExportConfig) -> ExportResult:
    """Connect to SQL Server, execute queries, export to .xlsx (UTF-8).

    Executes both the detail query and summary query. Results are written
    to .xlsx format using openpyxl (native UTF-8 support).

    Args:
        config: Validated ExportConfig.

    Returns:
        ExportResult with file path, row count, and timing metadata.
    """
    start_time = time.time()

    # Resolve template parameters into SQL
    detail_sql = _resolve_query(config.detail_query, config.parameters)
    summary_sql = _resolve_query(config.summary_query, config.parameters) if config.summary_query else ""

    try:
        with SQLServerConnector(config) as db:
            log.info("export.executing_detail")
            db.execute(detail_sql)
            rows = db.fetch_all_as_dicts()

            # Determine column names
            if rows:
                columns = list(rows[0].keys())
            elif db._cursor and db._cursor.description:
                columns = [col[0] for col in db._cursor.description]
            else:
                columns = []

            # Execute summary query if defined
            total_sales = 0.0
            if summary_sql:
                db.execute(summary_sql)
                total_sales = db.fetch_value()
                log.info("export.summary_result", total_sales=total_sales)

    except ConnectionError:
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        return ExportResult(
            config_name=config.output_filename,
            executed_at=datetime.now(),
            row_count=0,
            columns=[],
            file_path="",
            elapsed_seconds=round(elapsed, 2),
            error=str(e),
        )

    # Build DataFrame and write to .xlsx (UTF-8 via openpyxl)
    if rows:
        df = pd.DataFrame(rows)
    elif columns:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame()

    from src.export.writer import write_to_excel
    file_path = write_to_excel(df, config.output_dir, config.output_filename)

    elapsed = time.time() - start_time
    return ExportResult(
        config_name=config.output_filename,
        executed_at=datetime.now(),
        row_count=len(df),
        columns=list(df.columns),
        file_path=file_path,
        elapsed_seconds=round(elapsed, 2),
    )
