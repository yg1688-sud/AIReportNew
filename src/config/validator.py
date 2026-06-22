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

    Raises ValidationError on first invalid field.
    """
    from src.config.models import ExportConfig

    # Required string fields
    required = {
        "server": config.server,
        "database": config.database,
        "username": config.username,
        "detail_query": config.detail_query,
    }
    for field_name, value in required.items():
        if not value:
            raise ValidationError("export.yaml", field_name, f"'{field_name}' 为必填项")

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

    # SQL injection check: detail_query must not contain python string formatting
    if "%s" not in config.detail_query and "%(" in config.detail_query:
        raise ValidationError(
            "export.yaml", "detail_query",
            "请使用 {{param}} 占位符语法，而非 Python % 格式化"
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
