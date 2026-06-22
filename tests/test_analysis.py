"""TC-ANL: Template analysis tests."""

import pandas as pd
import pytest

from src.analysis.matcher import match_employees
from src.analysis.calculator import calculate_percentages, calculate_total
from src.config.models import AnalysisRow, EmployeeRow


class TestGroupAndSum:
    """TC-ANL-001/002: Employee sales aggregation."""

    def test_group_and_sum_sales_by_employee(self, mini_template):
        """Given order detail data → When match → Then per-employee sales summed."""
        raw_data = pd.DataFrame([
            {"销售店员ERPID": "14694", "销售金额": 5000.00, "销售门店": "保康"},
            {"销售店员ERPID": "14694", "销售金额": 2981.00, "销售门店": "保康"},
            {"销售店员ERPID": "6653", "销售金额": 148.00, "销售门店": "北碚6店"},
        ])

        matched, unmatched = match_employees(mini_template, raw_data)

        assert matched[0].sales_amount == 7981.00  # 5000 + 2981
        assert matched[1].sales_amount == 148.00
        assert len(unmatched) == 0

    def test_total_sales_matches_sum(self, mini_template):
        """Given matched rows → When calculate_total → Then total == sum of all."""
        rows = [
            AnalysisRow(seq=1, area="A", store="S1", name="N1", employee_id="1", sales_amount=100),
            AnalysisRow(seq=2, area="A", store="S2", name="N2", employee_id="2", sales_amount=200),
        ]
        total = calculate_total(rows)
        assert total.total_sales == 300.0


class TestPercentageCalculation:
    """TC-ANL-003/004: Percentage computation."""

    def test_sales_percentage_calculation(self):
        """Given total=76788.68 and employee=7981 → Then percentage ≈ 10.39%."""
        rows = [AnalysisRow(seq=1, area="", store="", name="", employee_id="1", sales_amount=7981.00)]
        result = calculate_percentages(rows, 76788.68)
        assert abs(result[0].percentage - 10.39) < 0.01

    def test_all_percentages_sum_to_approximately_100(self, mini_template):
        """Given matched rows with known total → Then percentages sum ≈ 100%."""
        rows = [
            AnalysisRow(seq=1, area="", store="", name="", employee_id="1", sales_amount=300),
            AnalysisRow(seq=2, area="", store="", name="", employee_id="2", sales_amount=700),
        ]
        result = calculate_percentages(rows, 1000.0)
        total_pct = sum(r.percentage for r in result)
        assert 99.9 <= total_pct <= 100.1


class TestUnmatchedHandling:
    """TC-ANL-005/006/007: Edge case matching."""

    def test_template_employee_not_in_data_gets_zero(self, mini_template):
        """Given empty data → Then all template rows have sales=0, matched=False."""
        df = pd.DataFrame(columns=["销售店员ERPID", "销售金额"])
        matched, _ = match_employees(mini_template, df)

        assert len(matched) == 2
        assert all(r.sales_amount == 0 for r in matched)
        assert all(not r.matched for r in matched)

    def test_data_employee_not_in_template_goes_to_unmatched(self, mini_template):
        """Given data with unknown employee → Then appears in unmatched list."""
        df = pd.DataFrame([
            {"销售店员ERPID": "99999", "销售金额": 500.00, "销售门店": "未知店"},
        ])

        matched, unmatched = match_employees(mini_template, df)
        assert len(unmatched) == 1
        assert unmatched[0]["销售店员ERPID"] == "99999"

    def test_unmatched_excluded_from_totals(self, mini_template):
        """Per FR-010: unmatched data NOT included in total."""
        df = pd.DataFrame([
            {"销售店员ERPID": "14694", "销售金额": 1000.00, "销售门店": "保康"},
            {"销售店员ERPID": "99999", "销售金额": 500.00, "销售门店": "未知店"},
        ])

        matched, unmatched = match_employees(mini_template, df)
        total = calculate_total(matched)

        # Only template employee (14694) in totals, 99999 excluded
        assert total.total_sales == 1000.00
        assert unmatched[0]["销售店员ERPID"] == "99999"

    def test_sort_order_preserved(self, mini_template):
        """TC-ANL-008: Results follow template employee_list order."""
        df = pd.DataFrame([
            {"销售店员ERPID": "6653", "销售金额": 200.00, "销售门店": "北碚6店"},
            {"销售店员ERPID": "14694", "销售金额": 100.00, "销售门店": "保康"},
        ])

        matched, _ = match_employees(mini_template, df)

        # Template order: 14694 first, 6653 second
        assert matched[0].employee_id == "14694"
        assert matched[1].employee_id == "6653"
