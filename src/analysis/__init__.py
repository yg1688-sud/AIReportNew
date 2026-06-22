"""Analysis module — template matching, aggregation, percentage calculation."""
from src.analysis.engine import run_analysis
from src.analysis.matcher import match_employees
from src.analysis.calculator import calculate_percentages, calculate_total

__all__ = ["run_analysis", "match_employees", "calculate_percentages", "calculate_total"]
