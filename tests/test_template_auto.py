"""Tests for auto_detect_group_column() in src/template/auto.py."""

import pandas as pd
import pytest

from src.template.auto import auto_detect_group_column


class TestAutoDetectGroupColumn:
    """Unit tests for auto_detect_group_column()."""

    def test_keyword_match_store(self):
        """Given DataFrame with '门店' column → returns '门店'."""
        df = pd.DataFrame({
            "门店": ["A", "B", "C"],
            "销售金额": [100, 200, 300],
        })
        result = auto_detect_group_column(df)
        assert result == "门店"

    def test_keyword_match_area(self):
        """Given DataFrame with '片区' column → returns '片区'."""
        df = pd.DataFrame({
            "片区": ["渝中", "北碚", "渝中"],
            "销售金额": [100, 200, 300],
        })
        result = auto_detect_group_column(df)
        assert result == "片区"

    def test_keyword_match_category(self):
        """Given DataFrame with '类别' column → returns '类别'."""
        df = pd.DataFrame({
            "类别": ["电子", "食品", "服装"],
            "销售额": [100, 200, 300],
        })
        result = auto_detect_group_column(df)
        assert result == "类别"

    def test_keyword_match_type(self):
        """Given DataFrame with '类型' column → returns '类型'."""
        df = pd.DataFrame({
            "类型": ["A", "B", "C"],
            "数量": [1, 2, 3],
        })
        result = auto_detect_group_column(df)
        assert result == "类型"

    def test_fallback_string_col(self):
        """Given no keyword match, but string col with 2-30 unique values → returns that col."""
        df = pd.DataFrame({
            "产品编号": ["P001", "P002", "P003", "P004"],
            "产品线": ["线A", "线B", "线A", "线B"],
            "金额": [100, 200, 150, 300],
        })
        result = auto_detect_group_column(df)
        assert result == "产品线"

    def test_no_suitable_column(self):
        """Given DataFrame with only numeric and single-value columns → returns None."""
        df = pd.DataFrame({
            "金额": [100, 200, 300],
            "数量": [1, 2, 3],
        })
        result = auto_detect_group_column(df)
        assert result is None

    def test_unique_values_out_of_range(self):
        """Given string col with > 30 unique values → skipped in fallback."""
        df = pd.DataFrame({
            "编号": [f"ID{i:03d}" for i in range(50)],
            "金额": list(range(50)),
        })
        # "编号" has 50 unique values, should be ignored
        result = auto_detect_group_column(df)
        assert result is None

    def test_single_unique_value_skipped(self):
        """Given string col with only 1 unique value → not selected."""
        df = pd.DataFrame({
            "状态": ["已审核", "已审核", "已审核"],
            "金额": [100, 200, 300],
        })
        result = auto_detect_group_column(df)
        assert result is None

    def test_keyword_substring_match(self):
        """Given '门店名称' → keyword match still works (substring)."""
        df = pd.DataFrame({
            "门店名称": ["保康", "北碚6店", "保康"],
            "销售金额": [100, 200, 300],
        })
        result = auto_detect_group_column(df)
        assert result == "门店名称"

    def test_priority_order_store_over_area(self):
        """门店 keyword has higher priority than 片区."""
        df = pd.DataFrame({
            "片区": ["渝中", "北碚"],
            "门店": ["保康", "北碚6店"],
            "金额": [100, 200],
        })
        result = auto_detect_group_column(df)
        assert result == "门店"

    def test_fewest_uniques_preferred(self):
        """Among fallback candidates, pick the one with fewest unique values."""
        df = pd.DataFrame({
            "color": ["红", "蓝", "红", "蓝", "绿"],   # 3 unique
            "shape": ["方", "圆", "方", "圆", "方"],   # 2 unique
            "金额": [100, 200, 150, 300, 250],
        })
        result = auto_detect_group_column(df)
        assert result == "shape"  # 2 unique < 3 unique
