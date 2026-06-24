"""Auto-generate AnalysisTemplate from query result data.

When export.yaml uses the queries:[] block with inline template config,
this module builds a complete AnalysisTemplate from the DataFrame columns
and unique values in the match-key column — no hand-written YAML needed.
"""

import pandas as pd

from src.config.models import (
    AnalysisTemplate,
    EmployeeRow,
    MatchKey,
    SortRule,
    SummaryRule,
    TemplateColumn,
    TemplateInlineConfig,
)

# ── Column format auto-detection ──

_MONEY_KEYWORDS = ["金额", "价格", "price", "amount", "pay", "sales", "cost"]
_PERCENT_KEYWORDS = ["占比", "百分比", "percent", "rate", "ratio"]
_NUMBER_KEYWORDS = ["数量", "num", "count", "qty"]


def _detect_format(col_name: str) -> str:
    """Auto-detect display format for a column by name."""
    lowered = col_name.lower()
    for kw in _MONEY_KEYWORDS:
        if kw in lowered:
            return "money"
    for kw in _PERCENT_KEYWORDS:
        if kw in lowered:
            return "percent"
    for kw in _NUMBER_KEYWORDS:
        if kw in lowered:
            return "number"
    return "text"


def auto_detect_value_field(data: pd.DataFrame) -> str:
    """Auto-detect the numeric sales column from DataFrame columns.

    Priority:
      1. Columns with '金额' in the name (Chinese sales amount)
      2. Numeric columns — pick the one with the largest sum.
    """
    # Priority 1: column name contains '金额'
    for col in data.columns:
        if "金额" in str(col):
            return str(col)

    # Priority 2: numeric column with largest sum
    numeric_cols = data.select_dtypes(include=["number"]).columns
    if len(numeric_cols) == 0:
        return ""

    best_col = ""
    best_sum = -1.0
    for col in numeric_cols:
        s = data[col].sum()
        if s > best_sum:
            best_sum = s
            best_col = str(col)
    return best_col


def _infer_name_column(data: pd.DataFrame) -> str:
    """Find a likely name/label column in the data.

    Priority: 姓名 > 名称 > name > 店员姓名 > first non-ID string column.
    """
    # Priority 1: explicit "姓名" column (not ERPID/ID)
    for col in data.columns:
        lowered = str(col)
        if "姓名" in lowered:
            return str(col)

    # Priority 2: other name-like columns
    for col in data.columns:
        lowered = str(col)
        if "名称" in lowered or "name" in lowered.lower():
            # Exclude columns that are IDs
            if "id" not in lowered.lower() and "erp" not in lowered.lower():
                return str(col)

    # Priority 3: "店员名" etc.
    for col in data.columns:
        lowered = str(col)
        if "店员" in lowered and "id" not in lowered.lower() and "erp" not in lowered.lower():
            return str(col)

    # Fallback: first string column that isn't an ID
    for col in data.columns:
        if data[col].dtype == object and "id" not in str(col).lower():
            return str(col)
    return ""


def auto_generate_template(
    data: pd.DataFrame,
    group_name: str,
    inline: TemplateInlineConfig,
) -> AnalysisTemplate:
    """Auto-generate an AnalysisTemplate from query result data.

    Steps:
      1. Create TemplateColumn for every DataFrame column (auto-detect format).
      2. Determine value_field: from inline config or auto-detect.
      3. Match key: from inline config.
      4. Generate employee_list from unique values in the match_key data column.
         Populate area/store/name/department from group_by / name columns.
      5. Apply sort_by or default sort.
    """
    # ── Step 1: Build columns ──
    columns = []
    for col_name in data.columns:
        fmt = _detect_format(str(col_name))
        columns.append(TemplateColumn(
            title=str(col_name),
            source_field=str(col_name),
            format=fmt,
            width=18 if fmt == "money" else 15,
        ))

    # ── Step 2: Determine value field ──
    value_field = inline.value_field
    if not value_field or value_field not in data.columns:
        value_field = auto_detect_value_field(data)
    name_col = _infer_name_column(data)

    # ── Step 3: Match key ──
    match_key = inline.match_key

    # ── Step 4: Generate employee_list from unique match-key values ──
    employee_list: list[EmployeeRow] = []
    if match_key.data_fields and match_key.data_fields[0] in data.columns:
        data_key = match_key.data_fields[0]
        unique_ids = data[data_key].dropna().astype(str).str.strip().unique()

        gb_fields = inline.group_by

        for seq, uid in enumerate(unique_ids, start=1):
            mask = data[data_key].astype(str).str.strip() == uid
            rows = data[mask]
            if rows.empty:
                continue

            first = rows.iloc[0]
            area = str(first[gb_fields[0]]) if len(gb_fields) > 0 and gb_fields[0] in data.columns else ""
            store = str(first[gb_fields[1]]) if len(gb_fields) > 1 and gb_fields[1] in data.columns else ""
            name = str(first[name_col]) if name_col and name_col in data.columns else uid
            dept = str(first[gb_fields[2]]) if len(gb_fields) > 2 and gb_fields[2] in data.columns else ""

            employee_list.append(EmployeeRow(
                seq=seq,
                area=area,
                store=store,
                name=name,
                employee_id=uid,
                department=dept,
            ))

    # ── Step 5: Sort ──
    sort_by = inline.sort_by if inline.sort_by else []
    if not sort_by and value_field:
        sort_by = [SortRule(field=value_field, order="desc")]

    # ── Step 6: Summary rules ──
    summary_rules = [
        SummaryRule(type="sum", source_field=value_field, target_field="sales_amount"),
        SummaryRule(type="percentage", source_field=value_field, target_field="percentage", base_field="total_sales"),
    ]

    # ── Step 7: Display name ──
    display_name = inline.display_name or group_name

    return AnalysisTemplate(
        name=group_name,
        display_name=display_name,
        columns=columns,
        group_by=inline.group_by,
        sort_by=sort_by,
        match_key=match_key,
        summary_rules=summary_rules,
        employee_list=employee_list,
        value_field=value_field,
    )
