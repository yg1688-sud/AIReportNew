"""Summary and percentage calculation utilities."""

from src.config.models import AnalysisRow, AnalysisTotal


def format_percentage(value: float) -> str:
    """Format a percentage value for display, handling very small values.

    Args:
        value: Percentage as a number (e.g. 10.39 for 10.39%).

    Returns:
        Formatted string like "10.39%" or "<0.01%" for tiny values.
    """
    if 0 < value < 0.01:
        return "<0.01%"
    return f"{value:.2f}%"


def calculate_percentages(rows: list[AnalysisRow], total_sales: float) -> list[AnalysisRow]:
    """Calculate each employee's sales percentage.

    percentage = employee.sales_amount / total_sales * 100

    Args:
        rows: Matched analysis rows with sales_amount populated.
        total_sales: The chain-wide total sales (from summary query).

    Returns:
        The same list with percentage field populated.
    """
    for row in rows:
        if total_sales > 0:
            row.percentage = round((row.sales_amount / total_sales) * 100, 2)
        else:
            row.percentage = 0.0
    return rows


def calculate_total(rows: list[AnalysisRow]) -> AnalysisTotal:
    """Compute the totals row from matched analysis rows.

    Args:
        rows: All analysis rows (matched + unmatched template rows).

    Returns:
        AnalysisTotal with aggregated values.
    """
    total_sales = sum(r.sales_amount for r in rows)
    active_employees = sum(1 for r in rows if r.sales_amount > 0)
    unique_stores = len(set(r.store for r in rows))

    return AnalysisTotal(
        total_sales=round(total_sales, 2),
        total_employees=active_employees,
        total_stores=unique_stores,
        total_percentage=100.0,
    )
