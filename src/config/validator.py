"""Configuration schema validation."""


class ValidationError(Exception):
    """Raised when config validation fails."""
    def __init__(self, file_path: str, field: str, message: str):
        self.file_path = file_path
        self.field = field
        self.message = message
        super().__init__(f"{file_path}: {field} — {message}")


def validate_export_config(config) -> None:
    """Validate ExportConfig required fields and constraints.

    In multi-query mode (queries dict is non-empty), detail_query at root
    level is optional. In single-query mode, detail_query is required.

    Raises ValidationError on first invalid field.
    """
    from src.config.models import ExportConfig, QueryGroupConfig

    has_queries = bool(config.queries)

    # Root-level connection is always required (as fallback for query groups)
    conn_required = {
        "server": config.server,
        "database": config.database,
        "username": config.username,
    }
    for field_name, value in conn_required.items():
        if not value:
            raise ValidationError("export.yaml", field_name, f"'{field_name}' 为必填项（根级默认连接）")

    # Port range
    if not (1 <= config.port <= 65535):
        raise ValidationError(
            "export.yaml", "port",
            f"端口号必须在 1-65535 范围内，当前值: {config.port}"
        )

    # Timeout range
    if not (5 <= config.timeout <= 300):
        raise ValidationError(
            "export.yaml", "timeout",
            f"超时时间必须在 5-300 秒范围内，当前值: {config.timeout}"
        )

    if has_queries:
        # Multi-query mode: validate each query group
        if not config.queries:
            raise ValidationError("export.yaml", "queries", "queries 块为空或格式错误")
    else:
        # Single-query mode: detail_query required at root level
        if not config.detail_query:
            raise ValidationError("export.yaml", "detail_query", "'detail_query' 为必填项")

        # SQL injection check
        if "%s" not in config.detail_query and "%(" in config.detail_query:
            raise ValidationError(
                "export.yaml", "detail_query",
                "请使用 {{param}} 占位符语法，而非 Python % 格式化"
            )

    # Validate query groups
    if has_queries:
        seen_names = set()
        for name, qg in config.queries.items():
            if name in seen_names:
                raise ValidationError(
                    "export.yaml", f"queries.{name}",
                    f"查询组名称 '{name}' 重复"
                )
            seen_names.add(name)
            validate_query_group(name, qg)


def validate_query_group(name: str, group) -> None:
    """Validate a single QueryGroupConfig."""
    from src.config.models import QueryGroupConfig

    if not group.detail_query:
        raise ValidationError(
            "export.yaml", f"queries.{name}.detail_query",
            f"查询组 '{name}' 的 detail_query 为必填项"
        )

    # Connection fields — optional, fall back to root-level if not set
    if group.port and not (1 <= group.port <= 65535):
        raise ValidationError(
            "export.yaml", f"queries.{name}.port",
            f"端口号必须在 1-65535 范围内，当前值: {group.port}"
        )
    if group.timeout and not (5 <= group.timeout <= 300):
        raise ValidationError(
            "export.yaml", f"queries.{name}.timeout",
            f"超时时间必须在 5-300 秒范围内，当前值: {group.timeout}"
        )
    # Password must use ${ENV_VAR} if set
    if group.password and not (group.password.startswith("${") and group.password.endswith("}")):
        raise ValidationError(
            "export.yaml", f"queries.{name}.password",
            "密码 MUST 使用 ${ENV_VAR} 环境变量引用，禁止明文密码"
        )

    # SQL injection check
    if "%s" not in group.detail_query and "%(" in group.detail_query:
        raise ValidationError(
            "export.yaml", f"queries.{name}.detail_query",
            "请使用 {{param}} 占位符语法，而非 Python % 格式化"
        )

    if group.template:
        _validate_inline_template(name, group.template)


def _validate_inline_template(group_name: str, tmpl) -> None:
    """Validate inline template configuration."""
    from src.config.models import TemplateInlineConfig

    if tmpl.match_key:
        tf = tmpl.match_key.template_fields
        df = tmpl.match_key.data_fields
        if tf and df and len(tf) != len(df):
            raise ValidationError(
                "export.yaml", f"queries.{group_name}.template.match_key",
                f"template_fields ({len(tf)}) 与 data_fields ({len(df)}) 数量不一致"
            )

    if not tmpl.group_by:
        raise ValidationError(
            "export.yaml", f"queries.{group_name}.template.group_by",
            "group_by 至少需要一个字段"
        )


def validate_template(template) -> None:
    """Validate AnalysisTemplate required fields and constraints.

    Raises ValidationError on first invalid field.
    """
    if not template.name:
        raise ValidationError("template.yaml", "name", "模版名称 'name' 为必填项")

    if not template.display_name:
        raise ValidationError("template.yaml", "display_name", "模版显示名称 'display_name' 为必填项")

    if not template.columns:
        raise ValidationError("template.yaml", "columns", "至少需要定义一个列")

    if template.match_key.template_fields and template.match_key.data_fields:
        if len(template.match_key.template_fields) != len(template.match_key.data_fields):
            raise ValidationError(
                "template.yaml", "match_key",
                f"template_fields ({len(template.match_key.template_fields)}) "
                f"与 data_fields ({len(template.match_key.data_fields)}) 数量不一致"
            )

    if not template.employee_list:
        raise ValidationError("template.yaml", "employee_list", "至少需要定义一个员工行")

    # Check employee_id uniqueness
    seen_ids = set()
    for emp in template.employee_list:
        if emp.employee_id in seen_ids:
            raise ValidationError(
                "template.yaml", "employee_list",
                f"员工ID '{emp.employee_id}' 重复（{emp.name}）"
            )
        seen_ids.add(emp.employee_id)
