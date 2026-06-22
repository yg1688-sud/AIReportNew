"""TC-CLI: CLI integration tests."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIListTemplates:
    """TC-CLI-002: list-templates command."""

    def test_list_templates(self, runner, temp_dir):
        """Given templates directory with YAML files → When list-templates → Then shows names."""
        import yaml
        tmpl_dir = temp_dir / "templates"
        tmpl_dir.mkdir()
        (tmpl_dir / "test.yaml").write_text("""
name: test-template
display_name: 测试模版
columns:
  - { title: "序号", source_field: "seq", format: "number" }
group_by: ["片区"]
match_key:
  template_fields: ["员工ID"]
  data_fields: ["销售店员ERPID"]
employee_list:
  - { seq: 1, area: "渝中", store: "保康", name: "测试", employee_id: "14694", department: "测试部门" }
""", encoding="utf-8")

        result = runner.invoke(cli, ["list-templates", "--templates-dir", str(tmpl_dir)])
        assert result.exit_code == 0
        assert "test-template" in result.output


class TestCLIValidate:
    """TC-CLI-003/004: validate command."""

    def test_validate_passes(self, runner, temp_dir):
        """Given valid config + template → When validate → Then exit 0 + '通过'."""
        config_dir = temp_dir / "configs"
        config_dir.mkdir()
        tmpl_dir = config_dir / "templates"
        tmpl_dir.mkdir()

        # Valid export config
        (config_dir / "export.yaml").write_text("""
server: localhost
port: 1433
database: TestDB
username: user
password: ${DB_PASSWORD}
detail_query: "SELECT 1"
parameters:
  start_date: "2026-06-01"
  end_date: "2026-06-16"
""", encoding="utf-8")

        # Valid template
        (tmpl_dir / "valid.yaml").write_text("""
name: valid-template
display_name: 有效模版
columns:
  - { title: "序号", source_field: "seq", format: "number" }
group_by: ["片区"]
match_key:
  template_fields: ["员工ID"]
  data_fields: ["销售店员ERPID"]
employee_list:
  - { seq: 1, area: "渝中", store: "保康", name: "测试", employee_id: "14694", department: "测试部门" }
""", encoding="utf-8")

        result = runner.invoke(cli, ["validate", "--config-dir", str(config_dir)])
        assert result.exit_code == 0
        assert "通过" in result.output

    def test_validate_detects_error(self, runner, temp_dir):
        """Given invalid config → When validate → Then exit non-zero + shows error."""
        config_dir = temp_dir / "configs"
        config_dir.mkdir()
        tmpl_dir = config_dir / "templates"
        tmpl_dir.mkdir()

        # Export config missing required fields
        (config_dir / "export.yaml").write_text("""
server: ""
port: 1433
database: ""
username: ""
password: ${DB_PASSWORD}
detail_query: "SELECT 1"
""", encoding="utf-8")

        result = runner.invoke(cli, ["validate", "--config-dir", str(config_dir)])
        # Should fail due to missing required fields
        assert result.exit_code != 0 or "问题" in result.output


class TestCLIHelp:
    """Basic CLI accessibility."""

    def test_cli_help(self, runner):
        """Given no args → When invoke → Then shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "export" in result.output
        assert "analyze" in result.output
        assert "list-templates" in result.output
        assert "validate" in result.output
