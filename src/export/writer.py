""".xlsx file writer for export results."""

from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()


class WriteError(Exception):
    """Raised when writing output file fails."""


def write_to_excel(df: pd.DataFrame, output_dir: str, filename: str) -> str:
    """Write a pandas DataFrame to an .xlsx file.

    Args:
        df: Data to write.
        output_dir: Target directory.
        filename: Output file name.

    Returns:
        Absolute path to the written file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Add timestamp to avoid overwrites
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".xlsx"
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = out_dir / f"{stem}_{ts}{suffix}"

    try:
        # Write using openpyxl engine for formatting support
        with pd.ExcelWriter(str(output_path), engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="导出数据")
            # Auto-adjust column widths
            ws = writer.sheets["导出数据"]
            for col_idx, col_name in enumerate(df.columns, 1):
                max_len = max(
                    len(str(col_name)),
                    df[col_name].astype(str).str.len().max() if len(df) > 0 else 0,
                )
                ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = min(max_len + 2, 50)
    except Exception as e:
        raise WriteError(f"写入 .xlsx 文件失败 ({output_path}): {e}") from e

    log.info("export.written", path=str(output_path), rows=len(df))
    return str(output_path)
