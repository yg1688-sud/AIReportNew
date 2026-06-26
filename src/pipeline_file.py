"""File analysis pipeline — analyze arbitrary .xlsx/.xls/.csv files.

Independent of pipeline.py — no SQL Server, no template matching, no employee concepts.
"""

import glob
import os
import time
from pathlib import Path

import pandas as pd
import structlog

from src.config.models import FileAnalysisResult

log = structlog.get_logger()

# Supported file extensions
_SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def _load_file(file_path: str) -> pd.DataFrame:
    """Load a supported table file into a DataFrame.

    Supports .xlsx, .xls (via pd.read_excel) and .csv (via pd.read_csv
    with automatic encoding detection: UTF-8 → GBK → Latin-1).

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        DataFrame with the file's contents.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path)

    if ext == ".csv":
        for encoding in ["utf-8", "gbk", "latin-1"]:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        # Last attempt with errors="replace"
        return pd.read_csv(file_path, encoding="utf-8", errors="replace")

    raise ValueError(f"不支持的文件格式: {ext}。支持的格式: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}")


def run_file_analysis(
    file_path: str,
    output_dir: str = "output/reports",
    value_col: str = "",
    name_col: str = "",
    group_col: str = "",
    generate_charts: bool = True,
    generate_pdf: bool = True,
    top_n: int = 10,
) -> FileAnalysisResult:
    """Run analysis on a single table file and generate reports.

    Steps:
      1. Load data via _load_file()
      2. Validate data is non-empty
      3. Auto-detect value_col, name_col, group_col if not provided
      4. Sort by value_col descending, compute 占比
      5. Generate charts
      6. Generate Excel report
      7. Generate PDF report (optional)

    Args:
        file_path: Path to the input file (.xlsx/.xls/.csv).
        output_dir: Directory for generated reports and charts.
        value_col: Numeric column name (auto-detect if empty).
        name_col: Label/name column name (auto-detect if empty).
        group_col: Categorical column for grouping (auto-detect if empty).
        generate_charts: Whether to generate chart PNGs.
        generate_pdf: Whether to generate a PDF report.
        top_n: Top N items for charts.

    Returns:
        FileAnalysisResult with all generated file paths and metadata.
    """
    file_label = os.path.splitext(os.path.basename(file_path))[0]
    ext = os.path.splitext(file_path)[1].lower()

    # ── Create per-file subdirectory under output_dir ──
    file_output_dir = os.path.join(output_dir, file_label)
    # Clean up previous reports before regenerating
    import shutil
    if os.path.isdir(file_output_dir):
        shutil.rmtree(file_output_dir)

    log.info("file_analysis.start", file=file_path)

    # ── Load data ──
    try:
        data = _load_file(file_path)
    except Exception as e:
        log.error("file_analysis.load_failed", file=file_path, error=str(e))
        return FileAnalysisResult(
            file_path=file_path,
            file_label=file_label,
            file_type=ext.lstrip("."),
            error=f"文件加载失败: {e}",
        )

    if data.empty:
        log.warning("file_analysis.empty", file=file_path)
        return FileAnalysisResult(
            file_path=file_path,
            file_label=file_label,
            file_type=ext.lstrip("."),
            row_count=0,
            col_count=len(data.columns),
            error="文件无数据",
        )

    row_count = len(data)
    col_count = len(data.columns)
    print(f"[OK] 加载: {row_count} 行, {col_count} 列")

    # ── Auto-detect columns ──
    from src.template.auto import (
        auto_detect_value_field,
        auto_detect_group_column,
        _infer_name_column,
    )

    resolved_value = value_col or auto_detect_value_field(data)
    resolved_name = name_col or _infer_name_column(data)
    resolved_group = group_col or auto_detect_group_column(data) or ""

    if not resolved_value:
        return FileAnalysisResult(
            file_path=file_path,
            file_label=file_label,
            file_type=ext.lstrip("."),
            row_count=row_count,
            col_count=col_count,
            name_col=resolved_name,
            group_col=resolved_group,
            error="无法检测到数值列，请使用 --value-col 指定",
        )

    if resolved_value not in data.columns:
        return FileAnalysisResult(
            file_path=file_path,
            file_label=file_label,
            file_type=ext.lstrip("."),
            row_count=row_count,
            col_count=col_count,
            name_col=resolved_name,
            group_col=resolved_group,
            error=f"指定的数值列 '{resolved_value}' 不存在于文件中",
        )

    print(f"[OK] 检测: 数值列=\"{resolved_value}\", 名称列=\"{resolved_name}\", 分组列=\"{resolved_group or '(无)'}\"")

    # ── Validate value_col is numeric ──
    if not pd.api.types.is_numeric_dtype(data[resolved_value]):
        # Try to convert
        try:
            data[resolved_value] = pd.to_numeric(data[resolved_value], errors="coerce").fillna(0)
        except Exception:
            return FileAnalysisResult(
                file_path=file_path,
                file_label=file_label,
                file_type=ext.lstrip("."),
                row_count=row_count,
                col_count=col_count,
                value_col=resolved_value,
                name_col=resolved_name,
                group_col=resolved_group,
                error=f"数值列 '{resolved_value}' 不是数值类型，无法分析",
            )

    # ── Sort by value descending ──
    data = data.sort_values(by=resolved_value, ascending=False).reset_index(drop=True)

    # ── Compute total ──
    total_value = data[resolved_value].sum()
    print(f"[DATA] 合计: ¥{total_value:,.2f}")

    # ── Generate charts ──
    chart_paths: list[str] = []
    if generate_charts:
        try:
            from src.chart.generator import generate_charts_for_file
            chart_paths = generate_charts_for_file(
                data=data,
                value_col=resolved_value,
                name_col=resolved_name,
                group_col=resolved_group if resolved_group else None,
                output_dir=file_output_dir,
                file_label=file_label,
                top_n=top_n,
            )
            if chart_paths:
                print(f"[OK] 图表: {len(chart_paths)} 张")
        except Exception as e:
            log.warning("file_analysis.chart_failed", file=file_path, error=str(e))

    # ── Generate Excel report ──
    try:
        from src.report.file_excel import generate_file_excel_report
        excel_path = generate_file_excel_report(
            data=data,
            value_col=resolved_value,
            output_dir=file_output_dir,
            file_label=file_label,
        )
        print(f"[OK] Excel 报告: {excel_path}")
    except Exception as e:
        log.error("file_analysis.excel_failed", file=file_path, error=str(e))
        return FileAnalysisResult(
            file_path=file_path,
            file_label=file_label,
            file_type=ext.lstrip("."),
            row_count=row_count,
            col_count=col_count,
            value_col=resolved_value,
            name_col=resolved_name,
            group_col=resolved_group,
            total_value=total_value,
            chart_paths=chart_paths,
            error=f"Excel 报告生成失败: {e}",
        )

    # ── Generate PDF report ──
    pdf_path = ""
    if generate_pdf:
        try:
            from src.report.file_pdf import generate_file_pdf_report
            pdf_path = generate_file_pdf_report(
                data=data,
                value_col=resolved_value,
                output_dir=file_output_dir,
                file_label=file_label,
                chart_paths=chart_paths,
            )
            print(f"[OK] PDF 报告: {pdf_path}")
        except Exception as e:
            log.warning("file_analysis.pdf_failed", file=file_path, error=str(e))

    return FileAnalysisResult(
        file_path=file_path,
        file_label=file_label,
        file_type=ext.lstrip("."),
        excel_path=excel_path,
        pdf_path=pdf_path,
        chart_paths=chart_paths,
        row_count=row_count,
        col_count=col_count,
        value_col=resolved_value,
        name_col=resolved_name,
        group_col=resolved_group,
        total_value=total_value,
    )


def run_file_analysis_batch(
    input_path: str,
    output_dir: str = "output/reports",
    exclude: str = "",
    **kwargs,
) -> list[FileAnalysisResult]:
    """Process a directory of table files or a single file.

    If input_path is a directory, glob for *.xlsx, *.xls, *.csv and process each.
    If input_path is a file, validate extension and process it.

    Args:
        input_path: Path to a file or directory.
        output_dir: Directory for generated reports.
        exclude: Comma-separated filename patterns to skip (supports wildcards).
        **kwargs: Passed through to run_file_analysis().

    Returns:
        List of FileAnalysisResult, one per processed file.
    """
    import fnmatch as _fnmatch
    exclude_patterns = [p.strip() for p in exclude.split(",") if p.strip()]

    results: list[FileAnalysisResult] = []

    if os.path.isdir(input_path):
        # Collect all supported files
        files: list[str] = []
        for ext in sorted(_SUPPORTED_EXTENSIONS):
            files.extend(glob.glob(os.path.join(input_path, f"*{ext}")))
        files.sort()

        # Apply exclude filters
        if exclude_patterns:
            before = len(files)
            files = [
                f for f in files
                if not any(_fnmatch.fnmatch(os.path.basename(f), pat) for pat in exclude_patterns)
            ]
            skipped = before - len(files)
            if skipped > 0:
                print(f"[INFO] 跳过 {skipped} 个文件（匹配排除规则）")

        if not files:
            print(f"[WARN] 目录中未找到支持的文件 (支持: {', '.join(sorted(_SUPPORTED_EXTENSIONS))})")
            return results

        for file_path in files:
            print(f"\n{'=' * 50}")
            print(f"[FILE] {os.path.basename(file_path)}")
            print(f"{'=' * 50}")

            result = run_file_analysis(
                file_path=file_path,
                output_dir=output_dir,
                **kwargs,
            )
            results.append(result)
    else:
        # Single file
        ext = os.path.splitext(input_path)[1].lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"不支持的文件格式: {ext}。支持的格式: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
            )

        result = run_file_analysis(
            file_path=input_path,
            output_dir=output_dir,
            **kwargs,
        )
        results.append(result)

    return results
