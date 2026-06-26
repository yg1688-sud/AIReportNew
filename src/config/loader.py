"""YAML/JSON configuration file loader."""

import json
import os
from pathlib import Path
from typing import Any

import yaml

from src.config.models import (
    ExportConfig,
    MatchKey,
    QueryGroupConfig,
    SortRule,
    TemplateInlineConfig,
)
from src.config.validator import validate_export_config, ValidationError


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


def _parse_match_key(mk: dict) -> MatchKey:
    """Parse a match_key block, supporting both long-form and shorthand.

    Long-form (existing):
        match_key:
          template_fields: ["员工ID"]
          data_fields: ["销售店员ERPID"]

    Shorthand (new):
        match_key:
          template: ["员工ID"]
          data: ["销售店员ERPID"]
    """
    template_fields = mk.get("template_fields", [])
    data_fields = mk.get("data_fields", [])

    # Support shorthand {template: [...], data: [...]}
    if not template_fields and "template" in mk:
        template_fields = mk["template"]
    if not data_fields and "data" in mk:
        data_fields = mk["data"]

    return MatchKey(
        template_fields=list(template_fields) if template_fields else [],
        data_fields=list(data_fields) if data_fields else [],
    )


def _parse_inline_template(tmpl_raw: dict | None) -> TemplateInlineConfig | None:
    """Parse an inline template block from export.yaml queries[].template."""
    if not tmpl_raw:
        return None

    mk_raw = tmpl_raw.get("match_key", {})
    match_key = _parse_match_key(mk_raw) if mk_raw else MatchKey()

    sort_by = [
        SortRule(field=s.get("field", ""), order=s.get("order", "asc"))
        for s in tmpl_raw.get("sort_by", [])
    ]

    return TemplateInlineConfig(
        group_by=tmpl_raw.get("group_by", []),
        match_key=match_key,
        sort_by=sort_by,
        display_name=tmpl_raw.get("display_name", ""),
        value_field=tmpl_raw.get("value_field", ""),
        columns=tmpl_raw.get("columns", []),
    )


def _parse_query_groups(raw_queries: dict, root_params: dict) -> dict[str, QueryGroupConfig]:
    """Parse the queries{} block into QueryGroupConfig dict.

    Root-level parameters are merged as defaults; group-level parameters
    take precedence for same-key overrides.
    """
    result: dict[str, QueryGroupConfig] = {}
    for name, qg_raw in raw_queries.items():
        # Merge parameters: root defaults + group overrides
        params = {**root_params, **qg_raw.get("parameters", {})}

        template = _parse_inline_template(qg_raw.get("template"))

        result[name] = QueryGroupConfig(
            name=name,
            detail_query=qg_raw.get("detail_query", ""),
            summary_query=qg_raw.get("summary_query", ""),
            parameters=params,
            output_filename=qg_raw.get("output_filename", f"{name}.xlsx"),
            template=template,
            analyze=qg_raw.get("analyze", True),
            # Per-group connection overrides (empty = inherit from root)
            server=qg_raw.get("server", ""),
            port=qg_raw.get("port", 0),
            database=qg_raw.get("database", ""),
            username=qg_raw.get("username", ""),
            password=qg_raw.get("password", ""),  # Raw — resolved at connect time
            timeout=qg_raw.get("timeout", 0),
        )
    return result


def load_export_config(file_path: str) -> ExportConfig:
    """Load export configuration from a YAML file.

    Supports two modes:
      - Single-query (old): detail_query / summary_query at root level.
      - Multi-query (new): a 'queries:' block with named query groups.
        Root-level parameters act as defaults for all groups.
    """
    data = _read_yaml(file_path)

    # FR-001: Password MUST use ${ENV_VAR} environment variable reference
    raw_password = data.get("password", "")
    if raw_password and not (raw_password.startswith("${") and raw_password.endswith("}")):
        raise ValidationError(
            file_path, "password",
            "密码 MUST 使用 ${ENV_VAR} 环境变量引用，禁止明文密码"
        )

    root_params: dict = data.get("parameters", {})

    # Parse queries block if present (multi-query mode)
    queries: dict[str, QueryGroupConfig] = {}
    if "queries" in data and data["queries"]:
        queries = _parse_query_groups(data["queries"], root_params)

    config = ExportConfig(
        server=data.get("server", ""),
        port=data.get("port", 1433),
        database=data.get("database", ""),
        username=data.get("username", ""),
        password=_resolve_env_vars(raw_password),
        detail_query=data.get("detail_query", ""),
        summary_query=data.get("summary_query", ""),
        parameters=root_params,
        output_dir=data.get("output_dir", "output/exports"),
        output_filename=data.get("output_filename", "export_result.xlsx"),
        timeout=data.get("timeout", 30),
        queries=queries,
    )

    validate_export_config(config)
    return config
