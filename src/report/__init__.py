"""Report module — Markdown and Excel report generation."""
from src.report.markdown import generate_markdown_report
from src.report.excel import generate_excel_report

__all__ = ["generate_markdown_report", "generate_excel_report"]
