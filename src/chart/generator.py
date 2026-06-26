"""Chart generation using matplotlib.

Generates bar charts, pie charts and funnel charts for sales analysis,
with automatic Chinese font discovery on Windows and Linux.
"""

import os
import structlog
from pathlib import Path

# Force non-interactive backend before any other matplotlib import
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

log = structlog.get_logger()

# ── Chinese font discovery ──

_WIN_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑 — best coverage
    "C:/Windows/Fonts/msyhbd.ttc",     # 微软雅黑 Bold
    "C:/Windows/Fonts/simhei.ttf",     # 黑体 — fallback
    "C:/Windows/Fonts/simsun.ttc",     # 宋体
    "C:/Windows/Fonts/simkai.ttf",     # 楷体
]

_LINUX_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]


def _discover_chinese_font() -> str | None:
    """Search for a Chinese-capable TTF/OTC font on the system."""
    candidates = _WIN_FONT_CANDIDATES + _LINUX_FONT_CANDIDATES
    for path in candidates:
        if os.path.isfile(path):
            log.info("chart.font_found", path=path)
            return path

    for f in fm.fontManager.ttflist:
        if any(kw in f.name.lower() for kw in ["hei", "ming", "song", "kai", "cjk", "chinese", "noto sans"]):
            log.info("chart.font_found_ml", name=f.name, path=f.fname)
            return f.fname

    log.warning("chart.no_chinese_font", hint="Chinese text may display as squares")
    return None


def _setup_matplotlib_chinese(font_path: str | None = None) -> str | None:
    """Configure matplotlib rcParams for Chinese font rendering."""
    path = font_path or _discover_chinese_font()
    if path:
        try:
            prop = fm.FontProperties(fname=path)
            font_name = prop.get_name()
            plt.rcParams["font.family"] = font_name
            plt.rcParams["font.sans-serif"] = [font_name]
            fm.fontManager.addfont(path)
            return path
        except Exception:
            log.warning("chart.font_setup_failed", path=path)
    return None


# ── Chart generators ──


def _truncate_label(label: str, max_len: int = 12) -> str:
    """Truncate a long label for display in chart axes/legends.

    Args:
        label: Original label string.
        max_len: Maximum character length before truncation.

    Returns:
        Truncated label with "…" suffix if too long.
    """
    s = str(label)
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _max_label_len(data: pd.DataFrame, col: str) -> int:
    """Return the max string length in a DataFrame column."""
    if col not in data.columns or data.empty:
        return 0
    return int(data[col].astype(str).str.len().max())


def generate_bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    output_path: str,
    top_n: int = 10,
    figsize: tuple = (14, 8),
    font_path: str | None = None,
    x_label: str = "",
    y_label: str = "",
) -> str:
    """Generate a horizontal bar chart PNG for top-N items."""
    _setup_matplotlib_chinese(font_path)

    # Take top_n largest, then sort ascending for barh (bottom=small, top=large)
    top_data = data.sort_values(by=y_col, ascending=False).head(top_n).copy()
    display_data = top_data.sort_values(by=y_col, ascending=True)
    others_sum = data[y_col].sum() - top_data[y_col].sum()

    if others_sum > 0:
        others_row = pd.DataFrame({x_col: ["其他"], y_col: [others_sum]})
        display_data = pd.concat([others_row, display_data], ignore_index=True)

    sorted_data = display_data

    # Dynamic figure width based on label length (long labels → wider canvas)
    max_label = _max_label_len(sorted_data, x_col)
    dynamic_width = max(12, min(26, 8 + max_label * 0.5))
    figsize = (dynamic_width, max(6, len(sorted_data) * 0.55))

    fig, ax = plt.subplots(figsize=figsize)

    # Reserve left margin for Y-axis labels (proportional to label length)
    left_margin = max(0.15, min(0.45, 0.12 + max_label * 0.018))
    fig.subplots_adjust(left=left_margin, right=0.95, top=0.93, bottom=0.08)

    bars = ax.barh(sorted_data[x_col], sorted_data[y_col])

    # Smaller font for Y-axis labels if they're long
    y_fontsize = 7 if max_label > 12 else (8 if max_label > 8 else 10)

    # Use bar_label for automatic label placement (avoids overlap)
    max_w = max(sorted_data[y_col]) if len(sorted_data) > 0 else 1
    labels = [f"￥{v:,.2f}" for v in sorted_data[y_col]]
    ax.bar_label(bars, labels=labels, padding=3, fontsize=8, fmt="%s")

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(x_label or y_col)
    ax.set_ylabel(y_label or x_col)
    ax.tick_params(axis="y", labelsize=y_fontsize)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    log.info("chart.bar_generated", path=output_path)
    return output_path


def generate_pie_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    output_path: str,
    figsize: tuple = (10, 10),
    font_path: str | None = None,
) -> str:
    """Generate a pie chart PNG for distribution visualization."""
    _setup_matplotlib_chinese(font_path)

    total = data[value_col].sum()
    if total <= 0:
        log.warning("chart.pie_zero_total", label_col=label_col)
        total = 1.0

    # Group slices under 3% into "其他"
    threshold = total * 0.03
    main = data[data[value_col] >= threshold].copy()
    small_sum = data[data[value_col] < threshold][value_col].sum()

    labels = [_truncate_label(l, 20) for l in main[label_col]]
    values = list(main[value_col])
    if small_sum > 0:
        labels.append("其他")
        values.append(small_sum)

    # Professional color palette
    cmap = plt.cm.Set3
    colors = [cmap(i / max(1, len(values) - 1)) for i in range(len(values))]

    fig, ax = plt.subplots(figsize=figsize)
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.75,
        colors=colors,
        wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
        textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")

    # Legend on the side
    ax.legend(
        wedges, labels,
        title="分类",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=8,
        title_fontsize=10,
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    fig.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    log.info("chart.pie_generated", path=output_path)
    return output_path


def generate_funnel_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    output_path: str,
    top_n: int = 10,
    figsize: tuple = (8, 6),
    font_path: str | None = None,
) -> str:
    """Generate a compact funnel chart showing top-N distribution."""
    _setup_matplotlib_chinese(font_path)

    sorted_data = data.sort_values(by=value_col, ascending=False).head(top_n).copy()
    total = sorted_data[value_col].sum()
    # Dynamic figure width based on label length
    max_label = _max_label_len(sorted_data, label_col)
    dynamic_width = max(8, min(16, 6 + max_label * 0.3))
    dynamic_figsize = (dynamic_width, max(5, len(sorted_data) * 0.55))

    if total <= 0:
        log.warning("chart.funnel_zero_total")
        return output_path

    labels = list(sorted_data[label_col])
    values = list(sorted_data[value_col])
    max_val = max(values) if values else 1.0

    # Color gradient — dark at top (largest), light at bottom
    n = len(values)
    colors = [plt.cm.Blues(0.35 + 0.65 * (i / max(1, n - 1))) for i in range(n)]

    fig, ax = plt.subplots(figsize=dynamic_figsize)

    # Reserve left/right margin for labels
    left_margin = max(0.15, min(0.45, 0.12 + max_label * 0.018))
    fig.subplots_adjust(left=left_margin, right=0.95, top=0.93, bottom=0.05)

    bar_h = 0.85  # bar height — tighter
    y_positions = list(reversed(range(n)))  # largest at top

    label_fontsize = 7 if max_label > 12 else (8 if max_label > 8 else 9)

    for i, (label, val) in enumerate(zip(labels, values)):
        w = val / max_val
        left = (1.0 - w) / 2

        ax.barh(y_positions[i], w, height=bar_h, left=left,
                color=colors[n - 1 - i],  # dark for largest (top)
                edgecolor="#ffffff", linewidth=0.8)

        # Name label — left side
        ax.text(left - 0.01, y_positions[i], label,
                ha="right", va="center", fontsize=label_fontsize)
        # Value label — right side
        ax.text(left + w + 0.01, y_positions[i], f"￥{val:,.0f}",
                ha="left", va="center", fontsize=8, color="#555555")

    ax.set_yticks([])
    ax.set_xlim(0, 1.20)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(bottom=False, labelbottom=False)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    log.info("chart.funnel_generated", path=output_path)
    return output_path


def generate_charts_for_analysis(
    result,
    output_dir: str = "output/reports",
    font_path: str | None = None,
) -> list[str]:
    """Generate all relevant charts for an analysis result."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    chart_paths: list[str] = []
    rows = result.rows

    if not rows:
        log.info("chart.no_data", template=result.template_name)
        return chart_paths

    df = pd.DataFrame([{
        "name": r.name,
        "employee_id": r.employee_id,
        "area": r.area,
        "store": r.store,
        "sales_amount": r.sales_amount,
        "percentage": r.percentage,
    } for r in rows if r.sales_amount > 0])

    if df.empty:
        log.info("chart.no_sales_data", template=result.template_name)
        return chart_paths

    # ── Bar chart ──
    bar_path = str(Path(output_dir) / f"chart_bar_{result.template_name}_{ts}.png")
    generate_bar_chart(
        data=df,
        x_col="name",
        y_col="sales_amount",
        title=f"{result.template_name} — 销售排行 Top 10",
        output_path=bar_path,
        top_n=10,
        font_path=font_path,
    )
    chart_paths.append(bar_path)

    # ── Pie chart (area first, store fallback) ──
    area_counts = df.groupby("area")["sales_amount"].sum().reset_index()
    area_counts = area_counts[area_counts["sales_amount"] > 0]

    if len(area_counts) > 1:
        pie_path = str(Path(output_dir) / f"chart_pie_{result.template_name}_{ts}.png")
        generate_pie_chart(
            data=area_counts,
            label_col="area",
            value_col="sales_amount",
            title=f"{result.template_name} — 片区销售分布",
            output_path=pie_path,
            font_path=font_path,
        )
        chart_paths.append(pie_path)
    else:
        store_counts = df.groupby("store")["sales_amount"].sum().reset_index()
        store_counts = store_counts[store_counts["sales_amount"] > 0]
        if len(store_counts) > 1:
            pie_path = str(Path(output_dir) / f"chart_pie_{result.template_name}_{ts}.png")
            generate_pie_chart(
                data=store_counts,
                label_col="store",
                value_col="sales_amount",
                title=f"{result.template_name} — 门店销售分布",
                output_path=pie_path,
                font_path=font_path,
            )
            chart_paths.append(pie_path)

    # ── Funnel chart ──
    if len(df) >= 3:
        funnel_path = str(Path(output_dir) / f"chart_funnel_{result.template_name}_{ts}.png")
        generate_funnel_chart(
            data=df,
            label_col="name",
            value_col="sales_amount",
            title=f"{result.template_name} — 销售漏斗 Top 10",
            output_path=funnel_path,
            top_n=10,
            font_path=font_path,
        )
        chart_paths.append(funnel_path)

    return chart_paths


def generate_charts_for_file(
    data: pd.DataFrame,
    value_col: str,
    name_col: str,
    group_col: str | None,
    output_dir: str = "output/reports",
    file_label: str = "file_analysis",
    top_n: int = 10,
    font_path: str | None = None,
) -> list[str]:
    """Generate all relevant charts from a raw DataFrame (no AnalysisResult needed).

    Always generates:
      - Bar chart: top-N by value_col, labeled by name_col
      - Funnel chart: top-N funnel (if >= 3 rows with positive values)

    Conditionally generates:
      - Pie chart: if group_col is provided, aggregate by group_col.

    Args:
        data: DataFrame sorted by value_col descending.
        value_col: Numeric column name for values.
        name_col: Column name for labels.
        group_col: Optional categorical column for pie chart grouping.
        output_dir: Directory for chart PNG files.
        file_label: Label used in chart file names.
        top_n: Top N items for bar and funnel charts.
        font_path: Optional Chinese font path.

    Returns:
        List of generated chart PNG file paths.
    """
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    chart_paths: list[str] = []

    if data.empty or value_col not in data.columns:
        log.info("chart.file_no_data", file=file_label)
        return chart_paths

    # Filter to rows with positive values for charts
    chart_data = data[data[value_col] > 0].copy()
    if chart_data.empty:
        log.info("chart.file_no_positive_values", file=file_label)
        return chart_paths

    # ── Bar chart ──
    bar_path = str(Path(output_dir) / f"chart_bar_{file_label}_{ts}.png")
    generate_bar_chart(
        data=chart_data,
        x_col=name_col,
        y_col=value_col,
        title=f"{file_label} — 排行 Top {top_n}",
        output_path=bar_path,
        top_n=top_n,
        font_path=font_path,
    )
    chart_paths.append(bar_path)

    # ── Pie chart (aggregate by group_col if provided) ──
    if group_col and group_col in data.columns:
        grouped = chart_data.groupby(group_col)[value_col].sum().reset_index()
        grouped = grouped[grouped[value_col] > 0]
        if len(grouped) >= 2:
            pie_path = str(Path(output_dir) / f"chart_pie_{file_label}_{ts}.png")
            generate_pie_chart(
                data=grouped,
                label_col=group_col,
                value_col=value_col,
                title=f"{file_label} — {group_col}分布",
                output_path=pie_path,
                font_path=font_path,
            )
            chart_paths.append(pie_path)
        else:
            log.info("chart.file_pie_skipped", group_col=group_col, groups=len(grouped))
    else:
        # Fallback: use name_col for pie chart if reasonable number of items
        if len(chart_data) >= 2 and len(chart_data) <= 30:
            pie_path = str(Path(output_dir) / f"chart_pie_{file_label}_{ts}.png")
            generate_pie_chart(
                data=chart_data,
                label_col=name_col,
                value_col=value_col,
                title=f"{file_label} — 分布",
                output_path=pie_path,
                font_path=font_path,
            )
            chart_paths.append(pie_path)

    # ── Funnel chart ──
    if len(chart_data) >= 3:
        funnel_path = str(Path(output_dir) / f"chart_funnel_{file_label}_{ts}.png")
        generate_funnel_chart(
            data=chart_data,
            label_col=name_col,
            value_col=value_col,
            title=f"{file_label} — 漏斗 Top {top_n}",
            output_path=funnel_path,
            top_n=top_n,
            font_path=font_path,
        )
        chart_paths.append(funnel_path)

    return chart_paths
