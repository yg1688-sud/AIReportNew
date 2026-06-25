"""TC-CLI: CLI integration tests."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIValidate:
    """TC-CLI-003/004: validate command."""

    def test_validate_passes(self, runner, temp_dir):
        """Given valid export.yaml with queries → When validate → Then exit 0 + '通过'."""
        config_path = temp_dir / "export.yaml"
        config_path.write_text("""
server: "localhost"
port: 1433
database: "TestDB"
username: "user"
password: "${DB_PASSWORD}"
queries:
  test-group:
    detail_query: "SELECT * FROM test"
    summary_query: "SELECT SUM(amount) FROM test"
    parameters:
      enterprise_id: "68288c8975fb4fa1a4b94da70b9f2765"
    output_filename: "test.xlsx"
    template:
      display_name: "Test"
      group_by: ["片区"]
      match_key:
        template: ["ID"]
        data: ["员工ID"]
      value_field: "销售金额"
""", encoding="utf-8")

        result = runner.invoke(cli, ["validate", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "通过" in result.output

    def test_validate_detects_error(self, runner, temp_dir):
        """Given invalid config → When validate → Then exit non-zero + shows error."""
        config_path = temp_dir / "export.yaml"
        config_path.write_text("""
server: ""
port: 1433
database: ""
username: ""
password: ${DB_PASSWORD}
""", encoding="utf-8")

        result = runner.invoke(cli, ["validate", "--config", str(config_path)])
        assert result.exit_code != 0 or "ERROR" in result.output


class TestCLIHelp:
    """Basic CLI accessibility."""

    def test_cli_help(self, runner):
        """Given no args → When invoke → Then shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "export" in result.output
        assert "show-queries" in result.output
        assert "validate" in result.output


class TestCLIShowQueries:
    """TC-CLI-005: show-queries command."""

    def test_show_queries(self, runner, temp_dir):
        """Given config with queries block → When show-queries → Then lists groups."""
        config_path = temp_dir / "export.yaml"
        config_path.write_text("""
server: "localhost"
port: 1433
database: "TestDB"
username: "user"
password: "${DB_PASSWORD}"
queries:
  group-a:
    detail_query: "SELECT 1"
    output_filename: "a.xlsx"
    template:
      group_by: ["片区"]
      match_key:
        template: ["ID"]
        data: ["员工ID"]
  group-b:
    detail_query: "SELECT 2"
    output_filename: "b.xlsx"
    template:
      group_by: ["门店"]
      match_key:
        template: ["门店"]
        data: ["销售门店"]
""", encoding="utf-8")

        result = runner.invoke(cli, ["show-queries", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "group-a" in result.output
        assert "group-b" in result.output


class TestAnalyzeFile:
    """TC-CLI-006: analyze-file command."""

    def test_analyze_file_basic(self, runner, sample_xlsx_path, temp_dir):
        """Basic invocation succeeds with exit code 0."""
        result = runner.invoke(cli, [
            "analyze-file", sample_xlsx_path,
            "--output-dir", str(temp_dir),
        ])
        assert result.exit_code == 0, result.output
        assert "加载" in result.output
        assert "Excel 报告" in result.output

    def test_analyze_file_no_pdf(self, runner, sample_xlsx_path, temp_dir):
        """--no-pdf flag produces only Excel."""
        result = runner.invoke(cli, [
            "analyze-file", sample_xlsx_path,
            "--output-dir", str(temp_dir),
            "--no-pdf",
        ])
        assert result.exit_code == 0
        assert "Excel 报告" in result.output

    def test_analyze_file_no_charts(self, runner, sample_xlsx_path, temp_dir):
        """--no-charts flag produces no chart PNGs."""
        result = runner.invoke(cli, [
            "analyze-file", sample_xlsx_path,
            "--output-dir", str(temp_dir),
            "--no-charts",
        ])
        assert result.exit_code == 0
        assert "0图" in result.output

    def test_analyze_file_custom_columns(self, runner, sample_xlsx_path, temp_dir):
        """Custom --value-col, --name-col, --group-col used."""
        result = runner.invoke(cli, [
            "analyze-file", sample_xlsx_path,
            "--output-dir", str(temp_dir),
            "--value-col", "销售数量",
            "--name-col", "日期",
            "--group-col", "备注",
        ])
        assert result.exit_code == 0
        assert '数值列="销售数量"' in result.output
        assert '名称列="日期"' in result.output
        assert '分组列="备注"' in result.output

    def test_analyze_file_nonexistent_path(self, runner):
        """Non-existent path fails before command executes (Click validation)."""
        result = runner.invoke(cli, ["analyze-file", "nonexistent_file.xlsx"])
        assert result.exit_code != 0

    def test_analyze_file_in_help(self, runner):
        """'analyze-file' appears in CLI help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "analyze-file" in result.output

    def test_analyze_file_csv(self, runner, sample_csv_path, temp_dir):
        """CSV input works via CLI."""
        result = runner.invoke(cli, [
            "analyze-file", sample_csv_path,
            "--output-dir", str(temp_dir),
            "--no-pdf",
        ])
        assert result.exit_code == 0, result.output
        assert "加载" in result.output
