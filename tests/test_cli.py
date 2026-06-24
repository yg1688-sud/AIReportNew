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
