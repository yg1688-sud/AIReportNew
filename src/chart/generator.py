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

    sorted_data = data.sort_values(by=y_col, ascending=False).head(top_n).copy()
    others_sum = data[y_col].sum() - sorted_data[y_col].sum()

    if others_sum > 0:
        sorted_data = pd.concat([
            sorted_data,
            pd.DataFrame({x_col: ["其他"], y_col: [others_sum]}),
        ], ignore_index=True)

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(sorted_data[x_col], sorted_data[y_col])

    for bar, val in zip(bars, sorted_data[y_col]):
        ax.text(
            bar.get_width() + max(sorted_data[y_col]) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"￥{val:,.2f}",
            va="center",
            fontsize=9,
        )

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(x_label or y_col)
    ax.set_ylabel(y_label or x_col)
    ax.invert_yaxis()
    fig.tight_layout()

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

    labels = list(main[label_col])
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
    figsize: tuple = (10, 14),
    font_path: str | None = None,
) -> str:
    """Generate a funnel chart PNG showing top-N distribution."""
    _setup_matplotlib_chinese(font_path)

    sorted_data = data.sort_values(by=value_col, ascending=False).head(top_n).copy()
    total = sorted_data[value_col].sum()

    if total <= 0:
        log.warning("chart.funnel_zero_total")
        return output_path

    labels = list(sorted_data[label_col])
    values = list(sorted_data[value_col])

    # Normalize widths for funnel effect
    max_val = max(values) if values else 1.0
    widths = [v / max_val for v in values]

    colors = plt.cm.Blues([0.3 + 0.7 * (i / max(1, len(values) - 1)) for i in range(len(values))])

    bar_height = 0.6
    y_positions = list(range(len(values)))

    fig, ax = plt.subplots(figsize=figsize)

    for i, (label, val, w) in enumerate(zip(labels, values, widths)):
        left = (1.0 - w) / 2
        ax.barh(y_positions[i], w, height=bar_height, left=left,
                color=colors[i], edgecolor="white", linewidth=1.5)

        # Label on the left
        ax.text(left - 0.02, y_positions[i], label,
                ha="right", va="center", fontsize=9)
        # Value — inside bar if wide, else right
        if w > 0.35:
            ax.text(left + w / 2, y_positions[i], f"￥{val:,.0f}",
                    ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        else:
            ax.text(left + w + 0.01, y_positions[i], f"￥{val:,.0f}",
                    ha="left", va="center", fontsize=8, color="#333333")

    ax.set_yticks([])
    ax.set_xlim(0, 1.30)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    fig.tight_layout()

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
