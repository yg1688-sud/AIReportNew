"""AIExport CLI — command-line interface for export, analysis, and reporting."""

import sys

import click
import structlog

from src.pipeline import run_full_pipeline, PipelineError
from src.config.loader import load_export_config
from src.config.validator import ValidationError
from src.export.executor import execute_export
from src.template.registry import TemplateRegistry, TemplateNotFoundError

log = structlog.get_logger()


@click.group()
@click.version_option(version="1.0.0", prog_name="ai-export")
def cli():
    """AIExport — AI-powered data export and template-based analysis.

    从 SQL Server 导出销售数据，按分析模版自动汇总计算，生成报告。
    """
    pass


@cli.command()
@click.option(
    "--template", "-t",
    required=True,
    help="分析模版名称（如 sanzhen-jiuti）",
)
@click.option(
    "--config", "-c",
    default="configs/export.yaml",
    help="导出配置文件路径",
    type=click.Path(exists=True),
)
@click.option("--date-start", default=None, help="覆盖起始日期 (YYYY-MM-DD)")
@click.option("--date-end", default=None, help="覆盖结束日期 (YYYY-MM-DD)")
@click.option(
    "--auto-date", is_flag=True, default=False,
    help="自动计算日期范围：16号导出1-15号，1号导出上月整月",
)
def run(template, config, date_start, date_end, auto_date):
    """一键执行全流程：导出 → 分析 → 报告。"""
    try:
        run_full_pipeline(
            config_path=config,
            template_name=template,
            date_start=date_start,
            date_end=date_end,
            auto_date=auto_date,
        )
    except (PipelineError, TemplateNotFoundError, ValidationError, FileNotFoundError) as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config", "-c",
    default="configs/export.yaml",
    help="导出配置文件路径",
    type=click.Path(exists=True),
)
def export(config):
    """仅执行数据导出（SQL Server → .xlsx）。"""
    try:
        export_config = load_export_config(config)
        result = execute_export(export_config)
        if result.error:
            click.echo(f"[ERROR] 导出失败: {result.error}", err=True)
            sys.exit(1)
        click.echo(f"[OK] 导出完成: {result.row_count} 行, 耗时 {result.elapsed_seconds}s")
        click.echo(f"   → {result.file_path}")
    except (ValidationError, FileNotFoundError) as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--template", "-t",
    required=True,
    help="分析模版名称",
)
@click.option(
    "--data", "-d",
    required=True,
    help="导出的 .xlsx 数据文件路径",
    type=click.Path(exists=True),
)
def analyze(template, data):
    """仅执行模版分析（使用已导出的数据）。

    需要先运行 export 命令导出数据，或已有 .xlsx 数据文件。
    """
    import pandas as pd
    from src.config.loader import load_export_config
    from src.analysis.engine import run_analysis

    try:
        registry = TemplateRegistry("configs/templates")
        tmpl = registry.get(template)
        raw_data = pd.read_excel(data)
        # Load config only for parameters
        config = load_export_config("configs/export.yaml")
        result = run_analysis(tmpl, raw_data, config)

        matched = result.metadata.matched_rows
        total = result.total_row.total_sales
        click.echo(f"[OK] 分析完成: 匹配 {matched}/{len(tmpl.employee_list)} 员工")
        click.echo(f"   [DATA] 合计销售额: ¥{total:,.2f}")
        if result.metadata.unmatched_rows:
            click.echo(f"   [WARN] {result.metadata.unmatched_rows} 名模版员工无销售记录")
        if result.unmatched_rows:
            click.echo(f"   [WARN] {len(result.unmatched_rows)} 行数据未匹配到模版员工")
    except (TemplateNotFoundError, FileNotFoundError, ValidationError) as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--templates-dir", default="configs/templates", help="模版目录")
def list_templates(templates_dir):
    """列出所有注册的分析模版。"""
    try:
        registry = TemplateRegistry(templates_dir)
        names = registry.list_all()
        if not names:
            click.echo("[WARN] 未找到任何分析模版")
            return
        click.echo(f"[LIST] 可用模版 ({len(names)}):")
        for name in names:
            tmpl = registry.get(name)
            click.echo(f"   • {name} — {tmpl.display_name}")
    except Exception as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)



@cli.command()
@click.option("--config-dir", default="configs", help="配置目录")
def validate(config_dir):
    """校验所有配置文件格式和完整性。"""
    from pathlib import Path

    errors = []
    ok_count = 0

    # Validate export config
    export_path = Path(config_dir) / "export.yaml"
    if export_path.exists():
        try:
            load_export_config(str(export_path))
            click.echo(f"[OK] export.yaml: 通过")
            ok_count += 1
        except (ValidationError, FileNotFoundError) as e:
            click.echo(f"[ERROR] export.yaml: {e}")
            errors.append(str(export_path))
    else:
        click.echo(f"[WARN] export.yaml: 文件不存在")

    # Validate all templates
    tmpl_dir = Path(config_dir) / "templates"
    if tmpl_dir.exists():
        for yaml_file in sorted(tmpl_dir.glob("*.yaml")):
            try:
                from src.config.loader import load_template
                load_template(str(yaml_file))
                click.echo(f"[OK] templates/{yaml_file.name}: 通过")
                ok_count += 1
            except (ValidationError, FileNotFoundError) as e:
                click.echo(f"[ERROR] templates/{yaml_file.name}: {e}")
                errors.append(str(yaml_file))
    else:
        click.echo(f"[WARN] templates/: 目录不存在")

    total = ok_count + len(errors)
    click.echo(f"\n校验完成: {ok_count}/{total} 通过")
    if errors:
        click.echo(f"[ERROR] {len(errors)} 个文件存在问题")
        sys.exit(1)


def main():
    """Entry point for python -m src.cli or ai-export command."""
    # Set UTF-8 mode on Windows for emoji/Chinese output
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    cli()


if __name__ == "__main__":
    main()
