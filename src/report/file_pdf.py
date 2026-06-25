"""Flexible PDF report generation for arbitrary DataFrames.

Unlike report/pdf.py which hardcodes 8 employee-specific columns, this module
generates reports showing all original columns plus a computed percentage column.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

log = structlog.get_logger()

# ── Chinese font discovery (shared logic with report/pdf.py) ──

_WIN_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simkai.ttf",
]

_LINUX_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]


def _discover_chinese_font() -> str | None:
    """Search for a Chinese-capable TTF/OTC font on the system."""
    for path in _WIN_FONT_CANDIDATES + _LINUX_FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def _register_fonts(font_path: str | None = None) -> tuple[str, str]:
    """Register a Chinese font with reportlab."""
    path = font_path or _discover_chinese_font()
    if not path:
        log.warning("file_pdf.no_chinese_font")
        return ("Helvetica", "Helvetica-Bold")

    try:
        font_name = "ChineseFontFile"
        pdfmetrics.registerFont(TTFont(font_name, path))
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily(font_name, normal=font_name, bold=font_name)
        log.info("file_pdf.font_registered", path=path, name=font_name)
        return (font_name, font_name)
    except Exception as e:
        log.warning("file_pdf.font_registration_failed", path=path, error=str(e))
        return ("Helvetica", "Helvetica-Bold")


def _build_styles(font_regular: str, font_bold: str) -> dict:
    """Build paragraph styles for the PDF report."""
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "FileReportTitle",
            parent=styles["Title"],
            fontName=font_bold,
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        "subtitle": ParagraphStyle(
            "FileReportSubtitle",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#666666"),
            spaceAfter=4 * mm,
        ),
        "section": ParagraphStyle(
            "FileSectionHeader",
            parent=styles["Heading2"],
            fontName=font_bold,
            fontSize=13,
            leading=18,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        ),
        "normal": ParagraphStyle(
            "FileNormal",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=9,
            leading=13,
        ),
        "th": ParagraphStyle(
            "FileTH",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "td": ParagraphStyle(
            "FileTD",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=7,
            leading=9,
        ),
        "td_r": ParagraphStyle(
            "FileTDRight",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=7,
            leading=9,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "FileFooter",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=7,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#999999"),
        ),
    }


def _footer_line(canvas, doc):
    """Draw page footer with page number and timestamp."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawCentredString(
        A4[0] / 2, 12 * mm,
        f"第 {canvas.getPageNumber()} 页 — AIExport 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    canvas.restoreState()


def _format_cell_value(val, col_name: str) -> str:
    """Format a cell value for PDF display."""
    from src.template.auto import _detect_format

    if val is None:
        return ""
    fmt = _detect_format(str(col_name))
    if fmt == "money" and isinstance(val, (int, float)):
        return f"¥{val:,.2f}"
    if fmt == "percent" and isinstance(val, (int, float)):
        return f"{val:.2f}%"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def generate_file_pdf_report(
    data: pd.DataFrame,
    value_col: str,
    output_dir: str = "output/reports",
    file_label: str = "file_analysis",
    chart_paths: list[str] | None = None,
    font_path: str | None = None,
) -> str:
    """Generate a flexible PDF report from an arbitrary DataFrame.

    Report structure:
      - Title: "文件数据分析报告: {file_label}"
      - Summary section: row count, value column, total value
      - Data table: all original columns + 占比
      - Total row
      - Embedded chart images
      - Page footer with timestamp

    Args:
        data: The DataFrame to report on (sorted by value_col descending).
        value_col: Name of the primary numeric column.
        output_dir: Directory for the output .pdf file.
        file_label: Stem of the source filename.
        chart_paths: Optional chart PNG paths to embed.
        font_path: Optional Chinese TTF font path.

    Returns:
        Absolute path to the generated .pdf file.
    """
    font_regular, font_bold = _register_fonts(font_path)
    styles = _build_styles(font_regular, font_bold)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out_dir / f"file_{file_label}_{ts}.pdf"

    # ── Resolve "占比" column name ──
    pct_col_name = "占比"
    if pct_col_name in data.columns:
        data = data.rename(columns={pct_col_name: "占比(原始)"})
        pct_col_name = "占比(分析)"

    # ── Compute percentage ──
    total = data[value_col].sum()
    data = data.copy()
    data[pct_col_name] = data[value_col].apply(
        lambda v: f"{v / total * 100:.2f}%" if total > 0 else "0.00%"
    )

    # ── Build document ──
    n_cols = len(data.columns)
    page_size = landscape(A4) if n_cols >= 6 else A4
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=page_size,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=f"{file_label} — AIExport 报告",
        author="AIExport",
    )

    story = []

    # ── Title ──
    story.append(Paragraph(f"文件数据分析报告: {file_label}", styles["title"]))
    story.append(Paragraph(
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 4 * mm))

    # ── Summary section ──
    story.append(Paragraph("汇总统计", styles["section"]))

    summary_data = [
        ["指  标", "数  值"],
        ["数据行数", str(len(data))],
        ["数值列", value_col],
        ["合计", f"¥{total:,.2f}"],
        ["列数", str(len(data.columns))],
    ]

    summary_table = Table(summary_data, colWidths=[50 * mm, 80 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B579A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F2F6FC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    # ── Detail data section ──
    story.append(Paragraph("详细数据", styles["section"]))

    if len(data) > 0:
        all_columns = list(data.columns)

        # Build table data
        table_data = [list(all_columns)]  # header row
        for _, row in data.iterrows():
            table_data.append([
                _format_cell_value(row[col], col) for col in all_columns
            ])

        # Calculate column widths
        avail_width = (page_size[0] if page_size else A4[0]) - 24 * mm
        col_width = max(avail_width / n_cols, 18 * mm)

        detail_table = Table(table_data, colWidths=[col_width] * n_cols, repeatRows=1)
        detail_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B579A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font_regular),
            ("FONTSIZE", (0, 0), (-1, 0), 6),
            ("FONTSIZE", (0, 1), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        # Alternating row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                detail_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F2F6FC")))

        # Right-align numeric columns
        from src.template.auto import _detect_format
        for col_idx, col_name in enumerate(all_columns):
            fmt = _detect_format(str(col_name))
            if fmt in ("money", "percent", "number") or col_name == pct_col_name:
                detail_style.append(("ALIGN", (col_idx, 0), (col_idx, -1), "RIGHT"))

        detail_table.setStyle(TableStyle(detail_style))
        story.append(detail_table)

        # Totals row
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(
            f"合计: ¥{total:,.2f}    "
            f"占比: 100.00%    "
            f"共 {len(data)} 行数据",
            ParagraphStyle(
                "TotalLine",
                parent=styles["normal"],
                fontName=font_bold,
                fontSize=9,
                alignment=TA_RIGHT,
            ),
        ))

    # ── Charts section ──
    if chart_paths:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("图表", styles["section"]))
        for cp in chart_paths:
            if os.path.isfile(cp):
                try:
                    img = Image(cp, width=240 * mm, height=120 * mm)
                    img.hAlign = "CENTER"
                    story.append(img)
                    story.append(Spacer(1, 4 * mm))
                except Exception as e:
                    log.warning("file_pdf.chart_embed_failed", path=cp, error=str(e))

    # ── Build ──
    doc.build(story, onFirstPage=_footer_line, onLaterPages=_footer_line)
    log.info("file_pdf.generated", path=str(filepath))
    return str(filepath)
