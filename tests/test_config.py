"""TC-CFG: Config loading and validation tests."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config.loader import load_export_config, load_template, ConfigLoadError
from src.config.models import ExportConfig, AnalysisTemplate
from src.config.validator import validate_export_config, validate_template, ValidationError


class TestExportConfigLoading:
    """TC-CFG-001: Load valid export config."""

    def test_load_valid_export_config(self, temp_dir):
        """Given valid YAML → When load → Then ExportConfig populated correctly."""
        config_path = temp_dir / "export.yaml"
        config_path.write_text("""
server: localhost
port: 1433
database: TestDB
username: readonly
password: ${DB_PASSWORD}
detail_query: "SELECT * FROM orders"
summary_query: "SELECT SUM(amount) FROM orders"
parameters:
  start_date: "2026-06-01"
  end_date: "2026-06-16"
timeout: 30
""", encoding="utf-8")

        config = load_export_config(str(config_path))

        assert config.server == "localhost"
        assert config.port == 1433
        assert config.database == "TestDB"
        assert config.detail_query is not None
        assert config.parameters["start_date"] == "2026-06-01"

    def test_load_nonexistent_config_raises_error(self):
        """TC-CFG-002: Given nonexistent file → When load → Then ConfigLoadError."""
        with pytest.raises(ConfigLoadError, match="配置文件未找到"):
            load_export_config("/nonexistent/path.yaml")

    def test_env_var_password_resolution(self, temp_dir):
        """Given password=${DB_PASSWORD} and env var set → When load → Then resolved."""
        os.environ["DB_PASSWORD"] = "test_secret_123"
        config_path = temp_dir / "export.yaml"
        config_path.write_text("""
server: localhost
port: 1433
database: TestDB
username: readonly
password: ${DB_PASSWORD}
detail_query: "SELECT 1"
""", encoding="utf-8")

        try:
            config = load_export_config(str(config_path))
            assert config.password == "test_secret_123"
        finally:
            del os.environ["DB_PASSWORD"]

    def test_plaintext_password_should_fail_validation(self, temp_dir):
        """Given password without ${} in YAML → When load → Then ValidationError (per FR-001)."""
        config_path = temp_dir / "bad_export.yaml"
        config_path.write_text("""
server: localhost
port: 1433
database: TestDB
username: readonly
password: plaintext_secret
detail_query: "SELECT 1"
""", encoding="utf-8")

        with pytest.raises(ValidationError, match="密码"):
            load_export_config(str(config_path))


class TestExportConfigValidation:
    """TC-CFG-003: Config field validation."""

    def test_missing_required_field(self):
        """Given ExportConfig missing 'server' → Then ValidationError."""
        config = ExportConfig(server="", database="db", username="u", detail_query="SELECT 1")
        with pytest.raises(ValidationError):
            validate_export_config(config)

    def test_invalid_port_range(self):
        """Given port=99999 → Then ValidationError."""
        config = ExportConfig(server="localhost", port=99999, database="db", username="u", detail_query="SELECT 1")
        with pytest.raises(ValidationError, match="端口"):
            validate_export_config(config)


class TestTemplateLoading:
    """TC-CFG-004: Template loading."""

    def test_load_valid_template(self, temp_dir):
        """Given valid template YAML → When load → Then AnalysisTemplate populated."""
        template_path = temp_dir / "template.yaml"
        template_path.write_text("""
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

        template = load_template(str(template_path))
        assert template.name == "test-template"
        assert template.display_name == "测试模版"
        assert len(template.employee_list) == 1
        assert template.employee_list[0].employee_id == "14694"

    def test_duplicate_employee_id_validation(self, temp_dir):
        """Given template with duplicate employee_id → Then ValidationError."""
        from src.config.models import EmployeeRow, TemplateColumn
        template = AnalysisTemplate(
            name="dup",
            display_name="重复测试",
            columns=[TemplateColumn(title="序号", source_field="seq", format="number")],
            employee_list=[
                EmployeeRow(seq=1, area="渝中", store="保康", name="A", employee_id="12345", department="测试"),
                EmployeeRow(seq=2, area="北碚", store="北碚6店", name="B", employee_id="12345", department="测试"),
            ],
        )
        with pytest.raises(ValidationError, match="重复") as exc_info:
            validate_template(template)
        assert "12345" in str(exc_info.value)
