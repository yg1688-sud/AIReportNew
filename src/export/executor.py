"""Query execution and data export orchestrator."""

import re
import time
from datetime import datetime

import pandas as pd
import structlog

from src.config.models import ExportConfig, ExportResult, QueryGroupConfig
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


def execute_export(
    config: ExportConfig,
    query_group: QueryGroupConfig | None = None,
) -> ExportResult:
    """Connect to SQL Server, execute queries, export to .xlsx (UTF-8).

    Executes both the detail query and summary query. Results are written
    to .xlsx format using openpyxl (native UTF-8 support).

    When query_group is provided, its detail_query / summary_query / parameters
    are used instead of the root-level config fields. Root-level parameters act
    as defaults; group-level parameters override them.

    Args:
        config: Validated ExportConfig.
        query_group: Optional QueryGroupConfig for multi-query mode.

    Returns:
        ExportResult with file path, row count, timing metadata, and
        cached summary_value.
    """
    start_time = time.time()

    # Determine which queries, parameters, output, and connection to use
    overrides: dict = {}
    if query_group:
        detail_query = query_group.detail_query
        summary_query = query_group.summary_query
        params = query_group.parameters
        filename = query_group.output_filename
        group_name = query_group.name
        # Per-group connection overrides
        if query_group.server:
            overrides["server"] = query_group.server
        if query_group.port:
            overrides["port"] = query_group.port
        if query_group.database:
            overrides["database"] = query_group.database
        if query_group.username:
            overrides["username"] = query_group.username
        if query_group.password:
            overrides["password"] = query_group.password
        if query_group.timeout:
            overrides["timeout"] = query_group.timeout
    else:
        detail_query = config.detail_query
        summary_query = config.summary_query
        params = config.parameters
        filename = config.output_filename
        group_name = ""

    # Resolve template parameters into SQL
    detail_sql = _resolve_query(detail_query, params)
    summary_sql = _resolve_query(summary_query, params) if summary_query else ""

    try:
        with SQLServerConnector(config, overrides) as db:
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
            summary_value = 0.0
            if summary_sql:
                db.execute(summary_sql)
                summary_value = db.fetch_value()
                log.info("export.summary_result", total_sales=summary_value)

    except ConnectionError:
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        return ExportResult(
            config_name=filename,
            executed_at=datetime.now(),
            row_count=0,
            columns=[],
            file_path="",
            elapsed_seconds=round(elapsed, 2),
            error=str(e),
            query_group_name=group_name,
        )

    # Build DataFrame and write to .xlsx (UTF-8 via openpyxl)
    if rows:
        df = pd.DataFrame(rows)
    elif columns:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame()

    from src.export.writer import write_to_excel
    file_path = write_to_excel(df, config.output_dir, filename)

    elapsed = time.time() - start_time
    return ExportResult(
        config_name=filename,
        executed_at=datetime.now(),
        row_count=len(df),
        columns=list(df.columns),
        file_path=file_path,
        elapsed_seconds=round(elapsed, 2),
        query_group_name=group_name,
        summary_value=summary_value,
    )
