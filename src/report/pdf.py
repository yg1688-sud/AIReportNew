"""PDF report generation using reportlab."""

import os
import structlog
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import HRFlowable

log = structlog.get_logger()

# ── Chinese font discovery (shared logic with chart/generator.py) ──

_WIN_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑 — best coverage
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",     # 黑体 — fallback
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simkai.ttf",
]

_LINUX_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]


def _display_width(s: str) -> int:
    """Approximate display width: CJK chars ≈ 2, ASCII ≈ 1."""
    w = 0
    for ch in str(s):
        if '一' <= ch <= '鿿' or '　' <= ch <= '〿' or '＀' <= ch <= '￯':
            w += 2
        else:
            w += 1
    return w


def _discover_chinese_font() -> str | None:
    """Search for a Chinese-capable TTF/OTC font on the system."""
    for path in _WIN_FONT_CANDIDATES + _LINUX_FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def _register_fonts(font_path: str | None = None) -> tuple[str, str]:
    """Register a Chinese font with reportlab.

    Returns (font_name_regular, font_name_bold) — both may be the same
    if no dedicated bold variant is found.
    """
    path = font_path or _discover_chinese_font()
    if not path:
        log.warning("pdf.no_chinese_font", hint="Chinese text will use Helvetica fallback")
        return ("Helvetica", "Helvetica-Bold")

    try:
        font_name = "ChineseFont"
        pdfmetrics.registerFont(TTFont(font_name, path))
        # Register as font family so bold/italic auto-resolution works
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily(font_name, normal=font_name, bold=font_name)
        log.info("pdf.font_registered", path=path, name=font_name)
        return (font_name, font_name)
    except Exception as e:
        log.warning("pdf.font_registration_failed", path=path, error=str(e))
        return ("Helvetica", "Helvetica-Bold")


# ── Styles ──

def _build_styles(font_regular: str, font_bold: str) -> dict:
    """Build paragraph styles for the PDF report."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=18,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
        spaceAfter=4 * mm,
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=13,
        leading=18,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    )

    normal_style = ParagraphStyle(
        "ChineseNormal",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=9,
        leading=13,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=7,
        leading=9,
        alignment=TA_CENTER,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=7,
        leading=9,
    )

    table_cell_right = ParagraphStyle(
        "TableCellRight",
        parent=table_cell_style,
        alignment=TA_RIGHT,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=7,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#999999"),
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "section": section_style,
        "normal": normal_style,
        "th": table_header_style,
        "td": table_cell_style,
        "td_r": table_cell_right,
        "footer": footer_style,
    }


# ── Page template with footer ──

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


# ── Main entry point ──

def generate_pdf_report(
    result,                  # AnalysisResult
    output_dir: str = "output/reports",
    display_name: str = "",
    chain_total: float | None = None,
    chart_paths: list[str] | None = None,
    font_path: str | None = None,
) -> str:
    """Generate a professional PDF report using reportlab.

    Report structure:
      - Title with date range
      - Summary statistics table
      - Detailed employee data table
      - Embedded chart images
      - Page footer with generation timestamp

    Args:
        result: The AnalysisResult to report on.
        output_dir: Directory for output files.
        display_name: Override display name.
        chain_total: Chain-wide total sales.
        chart_paths: Optional list of chart PNG paths to embed.
        font_path: Optional Chinese TTF font path.

    Returns:
        Path to the generated .pdf file.
    """
    font_regular, font_bold = _register_fonts(font_path)
    styles = _build_styles(font_regular, font_bold)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out_dir / f"report_{result.template_name}_{ts}.pdf"

    # Build document — landscape for wide tables, portrait otherwise
    page_size = landscape(A4) if result.rows else A4
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=page_size,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=f"{display_name or result.template_name} — AIExport 报告",
        author="AIExport",
    )

    story = []

    # ── Title ──
    date_start = result.metadata.date_range[0] if result.metadata.date_range else ""
    date_end = result.metadata.date_range[1] if result.metadata.date_range else ""
    date_str = f"{date_start} 至 {date_end}" if date_start else ""

    title_text = display_name or result.template_name
    story.append(Paragraph(title_text, styles["title"]))
    if date_str:
        story.append(Paragraph(f"分析期间: {date_str}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 4 * mm))

    # ── Summary Section ──
    story.append(Paragraph("汇总统计", styles["section"]))

    active_emp = result.total_row.total_employees
    total_emp = len(result.rows)
    actual_chain = chain_total if chain_total else result.chain_total
    pct_of_chain = (result.total_row.total_sales / actual_chain * 100) if actual_chain > 0 else 100.0

    summary_data = [
        ["指  标", "数  值"],
        ["连锁月度总销售额", f"¥{actual_chain:,.2f}"],
        ["模版员工合计", f"¥{result.total_row.total_sales:,.2f}"],
        ["占总连锁比例", f"{pct_of_chain:.2f}%"],
        ["有销售记录的员工数", f"{active_emp} / {total_emp}"],
        ["覆盖门店数", f"{result.total_row.total_stores}"],
        ["模版匹配率", f"{result.metadata.match_rate:.1%}"],
    ]

    summary_table = Table(summary_data, colWidths=[45 * mm, 65 * mm])
    summary_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B579A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        # Body rows
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

    # ── Detail Data Section ──
    story.append(Paragraph("详细数据", styles["section"]))

    if result.rows:
        # Header
        table_data = [["序号", "片区", "门店", "姓名", "员工ID", "销售金额", "占比", "部门"]]

        # Collect max content lengths for dynamic column sizing
        col_max_lens = [_display_width(h) for h in table_data[0]]
        for row in result.rows:
            from src.analysis.calculator import format_percentage
            pct_str = format_percentage(row.percentage)
            values = [
                str(row.seq),
                row.area,
                row.store,
                row.name,
                row.employee_id,
                f"¥{row.sales_amount:,.2f}",
                pct_str,
                row.department,
            ]
            for j, v in enumerate(values):
                col_max_lens[j] = max(col_max_lens[j], _display_width(str(v)))
            # Wrap long text cells in Paragraph for automatic line-wrapping
            wrapped_values = []
            for j, v in enumerate(values):
                # Wrap if display width exceeds ~1/8 of available width
                if _display_width(str(v)) > 15:
                    wrapped_values.append(Paragraph(str(v), styles["td"]))
                else:
                    wrapped_values.append(str(v))
            table_data.append(wrapped_values)

        # Calculate column widths dynamically based on content
        avail_width = (landscape(A4)[0] if result.rows else A4[0]) - 24 * mm
        total_len = sum(col_max_lens) or 1
        col_widths = [
            max(avail_width * cl / total_len, 15 * mm) for cl in col_max_lens
        ]
        # Ensure total doesn't exceed available width
        width_scale = avail_width / sum(col_widths)
        col_widths = [w * width_scale for w in col_widths]

        detail_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        detail_style = [
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B579A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font_regular),
            ("FONTSIZE", (0, 0), (-1, 0), 6),
            ("FONTSIZE", (0, 1), (-1, -1), 6),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (4, 0), (4, -1), "CENTER"),
            ("ALIGN", (5, 0), (5, -1), "RIGHT"),
            ("ALIGN", (6, 0), (6, -1), "RIGHT"),
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
            # Dim zero-sales rows
            if result.rows[i - 1].sales_amount == 0:
                detail_style.append(("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#999999")))

        detail_table.setStyle(TableStyle(detail_style))
        story.append(detail_table)

        # Totals row
        story.append(Spacer(1, 3 * mm))
        total_row = result.total_row
        story.append(Paragraph(
            f"合计销售金额: ¥{total_row.total_sales:,.2f}    "
            f"占比: 100.00%    "
            f"活跃员工: {total_row.total_employees}    "
            f"门店数: {total_row.total_stores}",
            ParagraphStyle(
                "TotalLine",
                parent=styles["normal"],
                fontName=font_bold,
                fontSize=9,
                alignment=TA_RIGHT,
            ),
        ))

    # ── Charts Section ──
    if chart_paths:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("图表", styles["section"]))
        for cp in chart_paths:
            if os.path.isfile(cp):
                try:
                    # Read actual image dimensions to preserve aspect ratio
                    from PIL import Image as PILImage
                    with PILImage.open(cp) as pil_img:
                        img_w, img_h = pil_img.size
                    # Fit within page: max 240mm wide × 160mm tall
                    max_w_mm = 240 * mm
                    max_h_mm = 160 * mm
                    aspect = img_h / img_w if img_w > 0 else 0.5
                    draw_w = max_w_mm
                    draw_h = draw_w * aspect
                    if draw_h > max_h_mm:
                        draw_h = max_h_mm
                        draw_w = draw_h / aspect
                    img = Image(cp, width=draw_w, height=draw_h)
                    img.hAlign = "CENTER"
                    story.append(img)
                    story.append(Spacer(1, 4 * mm))
                except Exception as e:
                    log.warning("pdf.chart_embed_failed", path=cp, error=str(e))

    # ── Build ──
    doc.build(story, onFirstPage=_footer_line, onLaterPages=_footer_line)
    log.info("report.pdf_generated", path=str(filepath))
    return str(filepath)
