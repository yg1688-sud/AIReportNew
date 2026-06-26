"""Flexible Excel report generation for arbitrary DataFrames.

Unlike report/excel.py which hardcodes 8 employee-specific columns, this module
generates reports showing all original columns plus a computed percentage column.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.drawing.image import Image as XLImage
except ImportError:
    Workbook = None
    Font = Alignment = Border = PatternFill = Side = None
    get_column_letter = None
    XLImage = None


# ── Style constants (mirrored from report/excel.py for independence) ──

_HEADER_FONT = None
_HEADER_FILL = None
_TOTAL_FONT = None
_THIN_BORDER = None
_MONEY_FORMAT = "#,##0.00"


def _init_styles():
    """Lazy-initialize openpyxl styles."""
    global _HEADER_FONT, _HEADER_FILL, _TOTAL_FONT, _THIN_BORDER
    if _HEADER_FONT is None and Font is not None:
        _HEADER_FONT = Font(name="微软雅黑", bold=True, size=11)
        _HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        _TOTAL_FONT = Font(name="微软雅黑", bold=True, size=11)
        _THIN_BORDER = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )


def generate_file_excel_report(
    data: pd.DataFrame,
    value_col: str,
    output_dir: str = "output/reports",
    file_label: str = "file_analysis",
    chart_paths: list[str] | None = None,
    show_summary: bool = True,
) -> str:
    """Generate a flexible Excel report from an arbitrary DataFrame.

    Report structure:
      Row 1: Title = "文件数据分析报告: {file_label}"
      Row 3-5: Summary stats (if show_summary=True)
      Row 7: Headers
      Row 8+: Data rows
      Last row: Total row

    Args:
        data: The DataFrame to report on (sorted by value_col descending).
        value_col: Name of the primary numeric column.
        output_dir: Directory for the output .xlsx file.
        file_label: Stem of the source filename (used in report title).
        chart_paths: Optional chart PNG paths to embed.

    Returns:
        Absolute path to the generated .xlsx file.
    """
    if Workbook is None:
        raise ImportError(
            "openpyxl is required for Excel report generation. Install with: pip install openpyxl"
        )

    _init_styles()

    # ── Resolve "占比" column name to avoid collision ──
    pct_col_name = "占比"
    if pct_col_name in data.columns:
        data = data.rename(columns={pct_col_name: "占比(原始)"})
        pct_col_name = "占比(分析)"

    # ── Compute percentage column ──
    total = data[value_col].sum()
    from src.analysis.calculator import format_percentage
    data = data.copy()
    data[pct_col_name] = data[value_col].apply(
        lambda v: format_percentage(v / total * 100) if total > 0 else "0.00%"
    )

    # ── Build workbook ──
    wb = Workbook()
    ws = wb.active
    sheet_title = file_label[:31]
    ws.title = sheet_title

    from src.template.auto import _detect_format

    all_columns = list(data.columns)
    n_cols = len(all_columns)

    # ── Row 1: Title ──
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
    title_cell = ws["A1"]
    title_cell.value = f"文件数据分析报告: {file_label}"
    title_cell.font = Font(name="微软雅黑", bold=True, size=14)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # ── Rows 3-5: Summary (optional) ──
    if show_summary:
        ws.cell(row=3, column=1, value="数据行数：").font = Font(bold=True)
        ws.cell(row=3, column=2, value=len(data))
        ws.cell(row=4, column=1, value="数值列：").font = Font(bold=True)
        ws.cell(row=4, column=2, value=value_col)
        ws.cell(row=5, column=1, value="合计：").font = Font(bold=True)
        total_cell = ws.cell(row=5, column=2, value=total)
        total_cell.number_format = _MONEY_FORMAT
        header_row = 7
    else:
        header_row = 3
    for col_idx, col_name in enumerate(all_columns, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=col_name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _THIN_BORDER

    # ── Data rows ──
    for i, (_, row) in enumerate(data.iterrows()):
        r = header_row + 1 + i
        max_text_len = 0
        for col_idx, col_name in enumerate(all_columns, 1):
            val = row[col_name]
            cell = ws.cell(row=r, column=col_idx, value=val)
            cell.border = _THIN_BORDER

            str_val = str(val) if val is not None else ""
            max_text_len = max(max_text_len, len(str_val))

            fmt = _detect_format(str(col_name))
            if fmt == "money" and isinstance(val, (int, float)):
                cell.number_format = _MONEY_FORMAT
                cell.alignment = Alignment(horizontal="center")
            elif fmt in ("percent", "number") or col_name == pct_col_name:
                cell.alignment = Alignment(horizontal="center")
            elif len(str_val) > 30:
                cell.alignment = Alignment(horizontal="center", wrap_text=True, vertical="top")
            else:
                cell.alignment = Alignment(horizontal="center")

        # Auto row height for rows with long text
        if max_text_len > 40:
            ws.row_dimensions[r].height = max(22, max_text_len // 2)
        elif max_text_len > 25:
            ws.row_dimensions[r].height = 18

    # ── Total row ──
    total_r = header_row + 1 + len(data)
    # Find the value_col index
    value_col_idx = list(all_columns).index(value_col) + 1 if value_col in all_columns else -1
    pct_col_idx = list(all_columns).index(pct_col_name) + 1 if pct_col_name in all_columns else -1

    for col_idx in range(1, n_cols + 1):
        cell = ws.cell(row=total_r, column=col_idx)
        cell.border = _THIN_BORDER
        cell.font = _TOTAL_FONT

    # First column: "合计" label
    ws.cell(row=total_r, column=1, value="合计").font = _TOTAL_FONT
    ws.cell(row=total_r, column=1).alignment = Alignment(horizontal="center")

    # Value column: total sum
    if value_col_idx > 0:
        sum_cell = ws.cell(row=total_r, column=value_col_idx, value=total)
        sum_cell.number_format = _MONEY_FORMAT
        sum_cell.font = _TOTAL_FONT

    # Percentage column: 100%
    if pct_col_idx > 0:
        pct_cell = ws.cell(row=total_r, column=pct_col_idx, value="100.00%")
        pct_cell.font = _TOTAL_FONT

    # ── Column widths ──
    for col_idx in range(1, n_cols + 1):
        max_len = len(str(all_columns[col_idx - 1])) + 2
        for r in range(header_row + 1, total_r):
            cell_val = ws.cell(row=r, column=col_idx).value
            if cell_val is not None:
                max_len = max(max_len, min(len(str(cell_val)), 80) + 2)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len, 80)

    # ── Embed chart images ──
    if chart_paths and XLImage is not None:
        img_row = total_r + 3
        for cp in chart_paths:
            if os.path.isfile(cp):
                try:
                    img = XLImage(cp)
                    img.width = min(img.width, 600)
                    img.height = img.height * (600 / max(img.width, 1))
                    ws.add_image(img, f"A{img_row}")
                    img_row += 35
                except Exception as e:
                    log.warning("file_excel.chart_embed_failed", path=cp, error=str(e))

    # ── Write file ──
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out_dir / f"file_{file_label}_{ts}.xlsx"
    wb.save(str(filepath))

    log.info("file_excel.generated", path=str(filepath))
    return str(filepath)
