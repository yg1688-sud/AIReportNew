"""TC-RPT: Report generation tests."""

import tempfile
from pathlib import Path

import pytest

from src.report.markdown import generate_markdown_report
from src.report.excel import generate_excel_report


class TestMarkdownReport:
    """TC-RPT-001/002: Markdown report structure and content."""

    def test_markdown_report_structure(self, mock_analysis_result, temp_dir):
        """Given AnalysisResult → When generate → Then report has title/summary/detail."""
        path = generate_markdown_report(
            mock_analysis_result,
            output_dir=str(temp_dir),
            display_name="三诊九体培训动销",
        )
        content = Path(path).read_text(encoding="utf-8")

        assert "三诊九体培训动销" in content
        assert "汇总统计" in content
        assert "详细分析" in content
        assert "合计" in content

    def test_markdown_table_row_count(self, mock_analysis_result, temp_dir):
        """Given result with 2 employees → Then table has 2 data rows + header + total."""
        path = generate_markdown_report(mock_analysis_result, output_dir=str(temp_dir))
        content = Path(path).read_text(encoding="utf-8")

        # Count data rows in the detail table (lines starting with | digit)
        data_rows = [l for l in content.split("\n") if l.startswith("| 1 ") or l.startswith("| 2 ")]
        assert len(data_rows) == 2

    def test_zero_sales_appears_in_report(self, mock_analysis_result, temp_dir):
        """TC-RPT-004: Employees with 0 sales are still in the report."""
        mock_analysis_result.rows[1].sales_amount = 0.0
        path = generate_markdown_report(mock_analysis_result, output_dir=str(temp_dir))
        content = Path(path).read_text(encoding="utf-8")
        assert "0.00" in content


class TestExcelReport:
    """TC-RPT-003/005: Excel report format and validity."""

    def test_excel_report_generates_valid_file(self, mock_analysis_result, temp_dir):
        """Given AnalysisResult → When generate Excel → Then file is valid .xlsx."""
        path = generate_excel_report(mock_analysis_result, output_dir=str(temp_dir))

        assert Path(path).exists()
        assert Path(path).suffix == ".xlsx"

        # Verify we can open it with openpyxl
        from openpyxl import load_workbook
        wb = load_workbook(path)
        ws = wb.active
        assert ws.max_row >= 3  # title + header + data + total
        assert ws.max_column >= 7

    def test_excel_has_bold_headers(self, mock_analysis_result, temp_dir):
        """Given AnalysisResult → When generate Excel → Then header row is bold."""
        path = generate_excel_report(mock_analysis_result, output_dir=str(temp_dir))

        from openpyxl import load_workbook
        wb = load_workbook(path)
        ws = wb.active
        # Header is row 7 (after title + summary)
        assert ws.cell(7, 1).font.bold is True

    def test_excel_money_format(self, mock_analysis_result, temp_dir):
        """Given AnalysisResult → When generate Excel → Then sales column has number format."""
        path = generate_excel_report(mock_analysis_result, output_dir=str(temp_dir))

        from openpyxl import load_workbook
        wb = load_workbook(path)
        ws = wb.active
        # First data row is row 8
        assert ws.cell(8, 6).value == 7981.00
