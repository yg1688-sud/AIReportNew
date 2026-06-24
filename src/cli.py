"""AIExport CLI — command-line interface for export, analysis, and reporting."""

import sys

import click
import structlog

from src.pipeline import run_full_pipeline, PipelineError
from src.config.loader import load_export_config
from src.config.validator import ValidationError
from src.export.executor import execute_export

log = structlog.get_logger()


@click.group()
@click.version_option(version="2.0.0", prog_name="ai-export")
def cli():
    """AIExport — AI-powered data export and auto-template analysis.

    从 SQL Server 导出销售数据，自动从查询结果生成分析模版，输出报告。
    """
    pass


@cli.command()
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
@click.option(
    "--query-group", "-q",
    default=None,
    help="仅运行指定的查询组（不指定则运行全部）",
)
@click.option(
    "--no-charts", is_flag=True, default=False,
    help="跳过图表生成",
)
@click.option(
    "--no-pdf", is_flag=True, default=False,
    help="跳过 PDF 报告（仅生成 Markdown + Excel）",
)
def run(config, date_start, date_end, auto_date, query_group, no_charts, no_pdf):
    """一键执行全流程：导出 → 分析 → 报告。

    \b
    示例：
      python -m src.cli run                        # 运行所有查询组
      python -m src.cli run -q sanzhen-jiuti       # 仅运行指定组
      python -m src.cli run --auto-date            # 自动日期 + 全量
      python -m src.cli run --no-pdf --no-charts   # 仅 Markdown + Excel
    """
    try:
        result = run_full_pipeline(
            config_path=config,
            date_start=date_start,
            date_end=date_end,
            auto_date=auto_date,
            query_group_filter=query_group,
            generate_charts=not no_charts,
            generate_pdf=not no_pdf,
        )
        if result.errors:
            sys.exit(1)
    except (PipelineError, ValidationError, FileNotFoundError) as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config", "-c",
    default="configs/export.yaml",
    help="导出配置文件路径",
    type=click.Path(exists=True),
)
@click.option(
    "--query-group", "-q",
    default=None,
    help="仅导出指定查询组（不指定则导出全部）",
)
def export(config, query_group):
    """仅执行数据导出（SQL Server → .xlsx）。

    默认导出全部查询组。
    """
    try:
        export_config = load_export_config(config)

        if not export_config.queries:
            click.echo("[ERROR] export.yaml 缺少 queries: 配置块", err=True)
            sys.exit(1)

        groups = export_config.queries
        if query_group:
            if query_group not in groups:
                click.echo(f"[ERROR] 查询组 '{query_group}' 未找到。可用: {', '.join(groups.keys())}", err=True)
                sys.exit(1)
            groups = {query_group: groups[query_group]}

        for name, qg in groups.items():
            result = execute_export(export_config, qg)
            if result.error:
                click.echo(f"[ERROR] [{name}] 导出失败: {result.error}", err=True)
            else:
                click.echo(f"[OK] [{name}] 导出完成: {result.row_count} 行, 耗时 {result.elapsed_seconds}s")
                click.echo(f"   → {result.file_path}")
    except (ValidationError, FileNotFoundError) as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", default="configs/export.yaml",
              type=click.Path(exists=True),
              help="导出配置文件路径")
def show_queries(config):
    """显示 export.yaml 中定义的查询组及其配置摘要。"""
    try:
        export_config = load_export_config(config)
        if export_config.queries:
            click.echo(f"[LIST] 查询组 ({len(export_config.queries)}):")
            for name, qg in export_config.queries.items():
                has_tmpl = "inline" if qg.template else "none"
                params_keys = list(qg.parameters.keys())

                # Connection source
                if qg.server or qg.database:
                    conn_src = f"{qg.server or '(继承)'}:{qg.port or '(继承)'}/{qg.database or '(继承)'}"
                else:
                    conn_src = "(继承根级)"

                click.echo(f"   • {name}")
                click.echo(f"     连接: {conn_src}")
                click.echo(f"     模版: {has_tmpl}")
                click.echo(f"     输出: {qg.output_filename}")
                click.echo(f"     参数: {params_keys}")
                if qg.template:
                    click.echo(f"     group_by: {qg.template.group_by}")
                    if qg.template.match_key.data_fields:
                        click.echo(f"     match_on: {qg.template.match_key.data_fields[0]}")
        else:
            click.echo("[INFO] export.yaml 缺少 queries: 配置块")
    except (ValidationError, FileNotFoundError) as e:
        click.echo(f"[ERROR] 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", default="configs/export.yaml",
              type=click.Path(exists=True),
              help="导出配置文件路径")
def validate(config):
    """校验 export.yaml 配置文件格式和完整性。"""
    try:
        load_export_config(config)
        click.echo(f"[OK] export.yaml: 通过")

        export_config = load_export_config(config)
        if export_config.queries:
            for name in export_config.queries:
                click.echo(f"[OK] queries.{name}: 通过")
            click.echo(f"\n校验完成: {1 + len(export_config.queries)} 项全部通过")
        else:
            click.echo("[WARN] 未找到 queries: 配置块")
    except (ValidationError, FileNotFoundError) as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for python -m src.cli or ai-export command."""
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    cli()


if __name__ == "__main__":
    main()
