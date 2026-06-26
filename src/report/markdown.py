"""Markdown report generation."""

from datetime import datetime
from pathlib import Path

import structlog

from src.analysis.calculator import format_percentage
from src.config.models import AnalysisResult

log = structlog.get_logger()

MARKDOWN_TEMPLATE = """# {display_name}

**分析期间**: {start_date} 至 {end_date}
**生成时间**: {generated_at}
**模版标识**: {template_name}

---

## 汇总统计

| 指标 | 值 |
|------|-----|
| 连锁月度总销售额 | ¥{total_sales:,.2f} |
| 有销售记录的员工数 | {active_employees} / {total_employees} |
| 覆盖门店数 | {total_stores} |
| 模版匹配率 | {match_rate:.1%} |

---

## 详细分析

| 序号 | 片区 | 门店 | 姓名 | 员工ID | 销售金额 | 占比 | 部门 |
|------|------|------|------|--------|----------|------|------|
{detail_rows}

---

## 合计

| 指标 | 值 |
|------|-----|
| 合计销售金额 | ¥{total_sales:,.2f} |
| 连锁月度总销售额 | ¥{chain_total:,.2f} |
| 占比 | {percentage} |

---

## 未匹配数据行

{unmatched_section}

---

*报告由 AIExport 自动生成 | {generated_at}*
"""


def generate_markdown_report(
    result: AnalysisResult,
    output_dir: str = "output/reports",
    display_name: str = "",
    chain_total: float | None = None,
) -> str:
    """Generate a Markdown report from analysis results.

    Args:
        result: The analysis result to report on.
        output_dir: Directory for the output file.
        display_name: Override display name (defaults to template name).
        chain_total: Chain-wide total sales for the summary (defaults to sum of all employees).

    Returns:
        Path to the generated .md file.
    """
    start_date = result.metadata.date_range[0] if result.metadata.date_range else ""
    end_date = result.metadata.date_range[1] if result.metadata.date_range else ""

    # Build detail rows
    detail_lines = []
    for row in result.rows:
        pct = format_percentage(row.percentage)
        dept = row.department.replace("|", "｜")  # Avoid breaking markdown table
        detail_lines.append(
            f"| {row.seq} | {row.area} | {row.store} | {row.name} "
            f"| {row.employee_id} | ¥{row.sales_amount:,.2f} | {pct} | {dept} |"
        )
    detail_text = "\n".join(detail_lines) if detail_lines else "| - | - | - | - | - | - | - | - |"

    # Unmatched section
    if result.unmatched_rows:
        unmatched_lines = [
            f"- 员工ID: {r.get('销售店员ERPID', 'N/A')}, "
            f"姓名: {r.get('销售店员姓名', 'N/A')}, "
            f"门店: {r.get('销售门店', 'N/A')}, "
            f"销售金额: ¥{float(r.get('销售金额', 0)):,.2f}"
            for r in result.unmatched_rows
        ]
        unmatched_text = "\n".join(unmatched_lines)
    else:
        unmatched_text = "无未匹配数据。所有导出数据均已匹配到模版中的员工。\n"

    # Chain total
    actual_chain_total = chain_total if chain_total else result.total_row.total_sales
    if actual_chain_total > 0:
        pct_of_chain = (result.total_row.total_sales / actual_chain_total) * 100
    else:
        pct_of_chain = 100.0

    report = MARKDOWN_TEMPLATE.format(
        display_name=display_name or result.template_name,
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        template_name=result.template_name,
        total_sales=result.total_row.total_sales,
        active_employees=result.total_row.total_employees,
        total_employees=len(result.rows),
        total_stores=result.total_row.total_stores,
        match_rate=result.metadata.match_rate,
        detail_rows=detail_text,
        chain_total=actual_chain_total,
        percentage=format_percentage(pct_of_chain),
        unmatched_section=unmatched_text,
    )

    # Write to file
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out_dir / f"report_{result.template_name}_{ts}.md"
    filepath.write_text(report, encoding="utf-8")

    log.info("report.markdown_generated", path=str(filepath))
    return str(filepath)
