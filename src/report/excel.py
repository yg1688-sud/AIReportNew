"""Excel report generation with formatting."""

import os
from datetime import datetime
from pathlib import Path

import structlog

from src.config.models import AnalysisResult

log = structlog.get_logger()

# Try importing openpyxl; provide clear error if not installed
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


HEADER_FONT = None
HEADER_FILL = None
TOTAL_FONT = None
THIN_BORDER = None
MONEY_FORMAT = '#,##0.00'
PERCENT_FORMAT = '0.00"%"'


def _init_styles():
    """Lazy-initialize styles after openpyxl is confirmed available."""
    global HEADER_FONT, HEADER_FILL, TOTAL_FONT, THIN_BORDER
    if HEADER_FONT is None and Font is not None:
        HEADER_FONT = Font(name="微软雅黑", bold=True, size=11)
        HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        TOTAL_FONT = Font(name="微软雅黑", bold=True, size=11)
        THIN_BORDER = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )


def generate_excel_report(
    result: AnalysisResult,
    output_dir: str = "output/reports",
    display_name: str = "",
    chain_total: float | None = None,
    chart_paths: list[str] | None = None,
) -> str:
    """Generate a formatted Excel report from analysis results.

    Args:
        result: The analysis result to report on.
        output_dir: Directory for the output file.
        display_name: Override display name for sheet title.
        chain_total: Chain-wide total sales override.
        chart_paths: Optional chart PNG paths to embed after the data table.

    Returns:
        Path to the generated .xlsx file.
    """
    if Workbook is None:
        raise ImportError("openpyxl is required for Excel report generation. Install with: pip install openpyxl")

    _init_styles()

    wb = Workbook()
    ws = wb.active
    sheet_title = (display_name or result.template_name)[:31]  # Excel sheet name limit
    ws.title = sheet_title

    date_range = f"{result.metadata.date_range[0]} 至 {result.metadata.date_range[1]}" \
        if result.metadata.date_range else ""

    # ── Title row ──
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = f"{display_name or result.template_name}（{date_range}）"
    title_cell.font = Font(name="微软雅黑", bold=True, size=14)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # ── Summary rows ──
    actual_chain = chain_total if chain_total else result.chain_total
    ws.cell(row=3, column=1, value="连锁月度总销售额：").font = Font(bold=True)
    ws.cell(row=3, column=3, value=actual_chain).number_format = MONEY_FORMAT
    ws.cell(row=4, column=1, value="模版员工合计：").font = Font(bold=True)
    ws.cell(row=4, column=3, value=result.total_row.total_sales).number_format = MONEY_FORMAT
    pct = (result.total_row.total_sales / actual_chain * 100) if actual_chain > 0 else 0.0
    ws.cell(row=5, column=1, value="占比：").font = Font(bold=True)
    ws.cell(row=5, column=3, value=f"{pct:.2f}%")
    ws.cell(row=6, column=1, value="有销售记录员工数：").font = Font(bold=True)
    ws.cell(row=6, column=3, value=f"{result.total_row.total_employees} / {len(result.rows)}")
    ws.cell(row=7, column=1, value="覆盖门店数：").font = Font(bold=True)
    ws.cell(row=7, column=3, value=result.total_row.total_stores)

    # ── Table header (row 7) ──
    headers = ["序号", "片区", "门店", "姓名", "员工ID", "销售金额", "占比", "部门"]
    header_row = 9
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # ── Data rows ──
    # Collect all values for auto-width calculation
    all_values: dict[int, list[str]] = {c: [] for c in range(1, 9)}
    for i, row in enumerate(result.rows):
        r = header_row + 1 + i
        ws.cell(row=r, column=1, value=row.seq).border = THIN_BORDER
        all_values[1].append(str(row.seq))
        ws.cell(row=r, column=2, value=row.area).border = THIN_BORDER
        all_values[2].append(str(row.area))
        ws.cell(row=r, column=3, value=row.store).border = THIN_BORDER
        all_values[3].append(str(row.store))
        ws.cell(row=r, column=4, value=row.name).border = THIN_BORDER
        all_values[4].append(str(row.name))
        ws.cell(row=r, column=5, value=row.employee_id).border = THIN_BORDER
        all_values[5].append(str(row.employee_id))

        sales_cell = ws.cell(row=r, column=6, value=row.sales_amount)
        sales_cell.number_format = MONEY_FORMAT
        sales_cell.alignment = Alignment(horizontal="right")
        sales_cell.border = THIN_BORDER
        all_values[6].append(f"{row.sales_amount:,.2f}")

        pct_cell = ws.cell(row=r, column=7, value=f"{row.percentage:.2f}%")
        pct_cell.alignment = Alignment(horizontal="right")
        pct_cell.border = THIN_BORDER
        all_values[7].append(f"{row.percentage:.2f}%")

        dept_cell = ws.cell(row=r, column=8, value=row.department)
        dept_cell.border = THIN_BORDER
        dept_cell.alignment = Alignment(wrap_text=True, vertical="top")
        all_values[8].append(str(row.department))

        # Set row height based on department text length (rough estimate for wrapping)
        dept_len = len(str(row.department))
        if dept_len > 40:
            ws.row_dimensions[r].height = max(30, dept_len // 2)
        elif dept_len > 25:
            ws.row_dimensions[r].height = 22

        # Highlight zero-sales rows
        if row.sales_amount == 0:
            for c in range(1, 9):
                ws.cell(row=r, column=c).font = Font(color="999999")

    # ── Total row ──
    total_r = header_row + 1 + len(result.rows)
    ws.merge_cells(start_row=total_r, start_column=1, end_row=total_r, end_column=5)
    total_label = ws.cell(row=total_r, column=1, value="合计")
    total_label.font = TOTAL_FONT
    total_label.alignment = Alignment(horizontal="center")
    total_label.border = THIN_BORDER
    for c in range(2, 6):
        ws.cell(row=total_r, column=c).border = THIN_BORDER
        ws.cell(row=total_r, column=c).font = TOTAL_FONT

    total_sales_cell = ws.cell(row=total_r, column=6, value=result.total_row.total_sales)
    total_sales_cell.number_format = MONEY_FORMAT
    total_sales_cell.font = TOTAL_FONT
    total_sales_cell.border = THIN_BORDER

    total_pct_cell = ws.cell(row=total_r, column=7, value="100.00%")
    total_pct_cell.font = TOTAL_FONT
    total_pct_cell.alignment = Alignment(horizontal="right")
    total_pct_cell.border = THIN_BORDER

    ws.cell(row=total_r, column=8).border = THIN_BORDER

    # ── Column widths (auto-calculated from content) ──
    # Headers + content max length, with sensible min/max per column role
    col_widths = []
    col_roles = ["narrow", "narrow", "medium", "medium", "narrow", "money", "narrow", "wide"]
    col_max = {"narrow": 14, "medium": 22, "money": 18, "wide": 60}
    col_min = {"narrow": 5, "medium": 8, "money": 12, "wide": 20}
    for c in range(1, 9):
        role = col_roles[c - 1]
        content_max = max((len(v) for v in all_values.get(c, [])), default=0)
        header_len = len(headers[c - 1])
        # Chinese chars ≈ 2x width
        raw_width = max(header_len * 2, content_max) + 2
        width = max(col_min[role], min(raw_width, col_max[role]))
        col_widths.append(width)
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # ── Embed chart images (if provided) ──
    if chart_paths and XLImage is not None:
        img_row = total_r + 3  # 2 rows gap after total row
        for cp in chart_paths:
            if os.path.isfile(cp):
                try:
                    img = XLImage(cp)
                    # Scale to fit within print area
                    img.width = min(img.width, 600)
                    img.height = img.height * (600 / max(img.width, 1))
                    cell_ref = f"A{img_row}"
                    ws.add_image(img, cell_ref)
                    img_row += 35  # ~35 rows per chart image
                except Exception as e:
                    log.warning("excel.chart_embed_failed", path=cp, error=str(e))

    # ── Write file ──
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out_dir / f"report_{result.template_name}_{ts}.xlsx"
    wb.save(str(filepath))

    log.info("report.excel_generated", path=str(filepath))
    return str(filepath)
