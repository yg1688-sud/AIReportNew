"""Integration tests for the file analysis pipeline."""

import os

import pandas as pd
import pytest

from src.pipeline_file import (
    run_file_analysis,
    run_file_analysis_batch,
    _load_file,
)
from src.config.models import FileAnalysisResult


class TestLoadFile:
    """Tests for _load_file()."""

    def test_load_xlsx(self, sample_xlsx_path):
        """Should load .xlsx into a DataFrame."""
        df = _load_file(sample_xlsx_path)
        assert len(df) == 5
        assert "销售金额" in df.columns

    def test_load_csv_utf8(self, sample_csv_path):
        """Should load UTF-8 .csv into a DataFrame."""
        df = _load_file(sample_csv_path)
        assert len(df) == 5
        assert "销售金额" in df.columns

    def test_load_csv_gbk(self, sample_csv_gbk_path):
        """Should load GBK .csv via encoding fallback."""
        df = _load_file(sample_csv_gbk_path)
        assert len(df) == 5
        assert "销售金额" in df.columns

    def test_load_unsupported_extension(self, temp_dir):
        """Should raise ValueError for unsupported extensions."""
        path = str(temp_dir / "test.txt")
        with open(path, "w") as f:
            f.write("hello")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            _load_file(path)


class TestRunFileAnalysis:
    """Integration tests for run_file_analysis()."""

    def test_end_to_end_xlsx(self, sample_xlsx_path, temp_dir):
        """Full pipeline: xlsx → charts + excel + pdf."""
        result = run_file_analysis(
            sample_xlsx_path,
            output_dir=str(temp_dir),
        )
        assert isinstance(result, FileAnalysisResult)
        assert result.error == ""
        assert result.row_count == 5
        assert result.value_col == "销售金额"
        assert result.name_col == "姓名"
        assert result.group_col == "门店"
        assert result.total_value > 0
        assert os.path.isfile(result.excel_path)
        assert os.path.isfile(result.pdf_path)
        assert len(result.chart_paths) >= 2  # bar + pie at minimum

    def test_custom_column_overrides(self, sample_xlsx_path, temp_dir):
        """Command-line column overrides take effect."""
        result = run_file_analysis(
            sample_xlsx_path,
            output_dir=str(temp_dir),
            value_col="销售数量",
            name_col="日期",
            group_col="备注",
        )
        assert result.value_col == "销售数量"
        assert result.name_col == "日期"
        assert result.group_col == "备注"

    def test_no_charts(self, sample_xlsx_path, temp_dir):
        """When generate_charts=False, no chart files produced."""
        result = run_file_analysis(
            sample_xlsx_path,
            output_dir=str(temp_dir),
            generate_charts=False,
        )
        assert len(result.chart_paths) == 0

    def test_no_pdf(self, sample_xlsx_path, temp_dir):
        """When generate_pdf=False, only Excel produced."""
        result = run_file_analysis(
            sample_xlsx_path,
            output_dir=str(temp_dir),
            generate_pdf=False,
        )
        assert result.pdf_path == ""
        assert os.path.isfile(result.excel_path)

    def test_empty_dataframe(self, temp_dir):
        """Empty DataFrame returns result with row_count=0."""
        path = str(temp_dir / "empty.xlsx")
        pd.DataFrame().to_excel(path, index=False)

        result = run_file_analysis(path, output_dir=str(temp_dir))
        assert result.row_count == 0
        assert "无数据" in result.error

    def test_no_numeric_column(self, temp_dir):
        """DataFrame with no numeric columns returns error."""
        path = str(temp_dir / "text_only.xlsx")
        pd.DataFrame({"名称": ["A", "B", "C"], "描述": ["x", "y", "z"]}).to_excel(path, index=False)

        result = run_file_analysis(path, output_dir=str(temp_dir))
        assert result.error != ""
        assert "数值列" in result.error

    def test_nonexistent_value_col(self, sample_xlsx_path, temp_dir):
        """Specifying a non-existent value_col returns error."""
        result = run_file_analysis(
            sample_xlsx_path,
            output_dir=str(temp_dir),
            value_col="不存在的列",
        )
        assert "不存在" in result.error

    def test_csv_end_to_end(self, sample_csv_path, temp_dir):
        """Pipeline works with .csv input."""
        result = run_file_analysis(
            sample_csv_path,
            output_dir=str(temp_dir),
        )
        assert result.error == ""
        assert result.file_type == "csv"
        assert result.row_count == 5
        assert os.path.isfile(result.excel_path)

    def test_csv_gbk_end_to_end(self, sample_csv_gbk_path, temp_dir):
        """Pipeline works with GBK-encoded .csv."""
        result = run_file_analysis(
            sample_csv_gbk_path,
            output_dir=str(temp_dir),
        )
        assert result.error == ""
        assert result.row_count == 5


class TestRunFileAnalysisBatch:
    """Tests for run_file_analysis_batch()."""

    def test_single_file(self, sample_xlsx_path, temp_dir):
        """Single file path processes one file."""
        results = run_file_analysis_batch(
            sample_xlsx_path,
            output_dir=str(temp_dir),
        )
        assert len(results) == 1
        assert results[0].error == ""

    def test_directory(self, sample_xlsx_path, temp_dir):
        """Directory processes all supported files."""
        # Create an extra file in the same directory
        dir_path = os.path.dirname(sample_xlsx_path)
        results = run_file_analysis_batch(
            dir_path,
            output_dir=str(temp_dir),
        )
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, FileAnalysisResult)

    def test_empty_directory(self, temp_dir):
        """Empty directory returns empty results list."""
        results = run_file_analysis_batch(
            str(temp_dir),
            output_dir=str(temp_dir),
        )
        assert results == []

    def test_unsupported_extension_raises(self, temp_dir):
        """Single file with unsupported extension raises ValueError."""
        path = str(temp_dir / "data.txt")
        with open(path, "w") as f:
            f.write("test")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            run_file_analysis_batch(path)
