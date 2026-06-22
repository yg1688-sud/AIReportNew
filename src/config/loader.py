"""YAML/JSON configuration file loader."""

import json
import os
from pathlib import Path
from typing import Any

import yaml

from src.config.models import (
    AnalysisTemplate,
    EmployeeRow,
    ExportConfig,
    MatchKey,
    SortRule,
    SummaryRule,
    TemplateColumn,
)
from src.config.validator import validate_export_config, validate_template, ValidationError


class ConfigLoadError(Exception):
    """Raised when a config file cannot be loaded or parsed."""


def _resolve_env_vars(value: str) -> str:
    """Resolve ${ENV_VAR} references in config values.

    Returns the env var value if set, empty string if not set.
    This ensures connection fails with clear auth error rather than
    passing a literal '${ENV_VAR}' string as password.
    """
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.environ.get(env_var, "")
    return value


def _read_yaml(file_path: str) -> dict[str, Any]:
    """Read and parse a YAML file."""
    path = Path(file_path)
    if not path.exists():
        raise ConfigLoadError(f"配置文件未找到: {file_path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigLoadError(f"YAML 解析失败 ({file_path}): {e}")


def load_export_config(file_path: str) -> ExportConfig:
    """Load export configuration from a YAML file."""
    data = _read_yaml(file_path)

    # FR-001: Password MUST use ${ENV_VAR} environment variable reference
    raw_password = data.get("password", "")
    if raw_password and not (raw_password.startswith("${") and raw_password.endswith("}")):
        raise ValidationError(
            file_path, "password",
            "密码 MUST 使用 ${ENV_VAR} 环境变量引用，禁止明文密码"
        )

    config = ExportConfig(
        server=data.get("server", ""),
        port=data.get("port", 1433),
        database=data.get("database", ""),
        username=data.get("username", ""),
        password=_resolve_env_vars(raw_password),
        detail_query=data.get("detail_query", ""),
        summary_query=data.get("summary_query", ""),
        parameters=data.get("parameters", {}),
        output_dir=data.get("output_dir", "output/exports"),
        output_filename=data.get("output_filename", "export_result.xlsx"),
        timeout=data.get("timeout", 30),
    )

    validate_export_config(config)
    return config


def load_template(file_path: str) -> AnalysisTemplate:
    """Load an analysis template from a YAML file."""
    data = _read_yaml(file_path)

    columns = [
        TemplateColumn(
            title=c.get("title", ""),
            source_field=c.get("source_field", ""),
            format=c.get("format", "text"),
            width=c.get("width", 15),
        )
        for c in data.get("columns", [])
    ]

    sort_by = [
        SortRule(field=s.get("field", ""), order=s.get("order", "asc"))
        for s in data.get("sort_by", [])
    ]

    mk = data.get("match_key", {})
    match_key = MatchKey(
        template_fields=mk.get("template_fields", []),
        data_fields=mk.get("data_fields", []),
    )

    summary_rules = [
        SummaryRule(
            type=r.get("type", "sum"),
            source_field=r.get("source_field", ""),
            target_field=r.get("target_field", ""),
            base_field=r.get("base_field", ""),
        )
        for r in data.get("summary_rules", [])
    ]

    employees = [
        EmployeeRow(
            seq=e.get("seq", i + 1),
            area=e.get("area", ""),
            store=e.get("store", ""),
            name=e.get("name", ""),
            employee_id=str(e.get("employee_id", "")),
            department=e.get("department", ""),
        )
        for i, e in enumerate(data.get("employee_list", []))
    ]

    template = AnalysisTemplate(
        name=data.get("name", ""),
        display_name=data.get("display_name", ""),
        description=data.get("description", ""),
        columns=columns,
        group_by=data.get("group_by", []),
        sort_by=sort_by,
        match_key=match_key,
        summary_rules=summary_rules,
        employee_list=employees,
    )

    validate_template(template)
    return template
