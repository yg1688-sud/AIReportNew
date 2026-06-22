"""Employee-to-data matching logic."""

import pandas as pd
import structlog

from src.config.models import AnalysisRow, AnalysisTemplate

log = structlog.get_logger()


def match_employees(
    template: AnalysisTemplate,
    data: pd.DataFrame,
) -> tuple[list[AnalysisRow], list[dict]]:
    """Match template employee rows to data rows.

    Strategy:
      1. Exact match: template employee_id == data staff_id
      2. If an employee appears in multiple data rows, sum their sales.
      3. Template employees not found in data → sales_amount = 0, matched = False.
      4. Data rows not matching any template employee → unmatched_rows.

    Args:
        template: The analysis template with pre-defined employee list.
        data: Raw export data as pandas DataFrame.

    Returns:
        (matched_rows, unmatched_data_rows)
    """
    if template.match_key.data_fields and template.match_key.template_fields:
        data_key_field = template.match_key.data_fields[0]  # e.g., "销售店员ERPID"
    else:
        data_key_field = "销售店员ERPID"

    # Ensure data key column is string type for reliable matching
    if data_key_field in data.columns:
        data[data_key_field] = data[data_key_field].astype(str).str.strip()
    else:
        log.warning("matcher.missing_key_column", column=data_key_field)
        # Return all template rows as unmatched
        rows = [
            AnalysisRow(
                seq=emp.seq, area=emp.area, store=emp.store,
                name=emp.name, employee_id=emp.employee_id,
                sales_amount=0.0, department=emp.department, matched=False,
            )
            for emp in template.employee_list
        ]
        return rows, data.to_dict("records") if len(data) > 0 else []

    # Build a set of matched data indices
    matched_data_indices: set = set()
    matched_rows: list[AnalysisRow] = []

    # Determine sales column name
    sales_col = "销售金额" if "销售金额" in data.columns else None

    for emp in template.employee_list:
        mask = data[data_key_field] == emp.employee_id
        matched_subset = data[mask]

        if len(matched_subset) > 0:
            sales_sum = float(matched_subset[sales_col].sum()) if sales_col else 0.0
            matched_data_indices.update(matched_subset.index.tolist())
            matched_rows.append(AnalysisRow(
                seq=emp.seq,
                area=emp.area,
                store=emp.store,
                name=emp.name,
                employee_id=emp.employee_id,
                sales_amount=round(sales_sum, 2),
                department=emp.department,
                matched=True,
            ))
        else:
            matched_rows.append(AnalysisRow(
                seq=emp.seq,
                area=emp.area,
                store=emp.store,
                name=emp.name,
                employee_id=emp.employee_id,
                sales_amount=0.0,
                department=emp.department,
                matched=False,
            ))

    # Collect unmatched data rows
    unmatched_indices = set(data.index) - matched_data_indices
    unmatched_data = data.loc[list(unmatched_indices)].to_dict("records") if unmatched_indices else []

    log.info(
        "matcher.result",
        template_rows=len(template.employee_list),
        matched=sum(1 for r in matched_rows if r.matched),
        not_matched=sum(1 for r in matched_rows if not r.matched),
        unmatched_data=len(unmatched_data),
    )

    return matched_rows, unmatched_data
