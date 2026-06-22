"""Shared pytest fixtures and mocks for AIExport tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config.models import (
    AnalysisResult,
    AnalysisRow,
    AnalysisTemplate,
    AnalysisTotal,
    AnalysisMetadata,
    EmployeeRow,
    ExportConfig,
    MatchKey,
    SortRule,
    SummaryRule,
    TemplateColumn,
)


# ── Path helpers ──

@pytest.fixture
def temp_dir():
    """Create a temporary directory, cleaned up after test."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    p = Path(__file__).parent / "fixtures"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Sample data ──

@pytest.fixture
def sample_order_data():
    """Minimal sample order data matching the export query schema."""
    return [
        {
            "订单号": "ORD001",
            "商品ERPID": "150087",
            "成本价": 50.00,
            "销售单价": 79.80,
            "销售数量": 2,
            "销售金额": 159.60,
            "支付时间": "2026-06-05 10:30:00",
            "销售门店ID": "ST001",
            "销售门店": "保康",
            "销售店员ERPID": "14694",
            "销售店员姓名": "梅朱琳",
        },
        {
            "订单号": "ORD002",
            "商品ERPID": "215254",
            "成本价": 30.00,
            "销售单价": 49.90,
            "销售数量": 1,
            "销售金额": 49.90,
            "支付时间": "2026-06-06 14:00:00",
            "销售门店ID": "ST002",
            "销售门店": "北碚6店",
            "销售店员ERPID": "6653",
            "销售店员姓名": "刘敏",
        },
    ]


@pytest.fixture
def sample_order_df(sample_order_data):
    """Sample order data as pandas DataFrame."""
    return pd.DataFrame(sample_order_data)


# ── Mock SQL Server connector ──

@pytest.fixture
def mock_sql_connection():
    """Mock pymssql connection returning controllable result sets."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Default: return sample data
    mock_cursor.description = [
        ("订单号",), ("商品ERPID",), ("成本价",), ("销售单价",),
        ("销售数量",), ("销售金额",), ("支付时间",), ("销售门店ID",),
        ("销售门店",), ("销售店员ERPID",), ("销售店员姓名",),
    ]
    mock_cursor.fetchall.return_value = [
        ("ORD001", "150087", 50.00, 79.80, 2, 159.60, "2026-06-05 10:30:00",
         "ST001", "保康", "14694", "梅朱琳"),
    ]

    mock_conn.cursor.return_value = mock_cursor
    # Context manager support
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    return mock_conn


# ── Config fixtures ──

@pytest.fixture
def valid_export_config_dict():
    """Minimal valid export config as dict for loader testing."""
    return {
        "server": "localhost",
        "port": 1433,
        "database": "TestDB",
        "username": "test_user",
        "password": "${DB_PASSWORD}",
        "detail_query": "SELECT * FROM orders WHERE date >= %s AND date < %s",
        "summary_query": "SELECT SUM(amount) FROM orders WHERE date >= %s AND date < %s",
        "parameters": {
            "start_date": "2026-06-01",
            "end_date": "2026-06-16",
        },
        "timeout": 30,
    }


@pytest.fixture
def valid_export_config():
    """A valid ExportConfig object."""
    return ExportConfig(
        server="localhost",
        port=1433,
        database="TestDB",
        username="test_user",
        password="secret",
        detail_query="SELECT * FROM orders",
        summary_query="SELECT SUM(amount) FROM orders",
        parameters={"start_date": "2026-06-01", "end_date": "2026-06-16"},
    )


# ── Template fixtures ──

@pytest.fixture
def mini_template():
    """A minimal analysis template with 2 employees."""
    return AnalysisTemplate(
        name="mini-test",
        display_name="迷你测试模版",
        columns=[
            TemplateColumn(title="序号", source_field="seq", format="number", width=6),
            TemplateColumn(title="姓名", source_field="name", format="text", width=10),
            TemplateColumn(title="销售金额", source_field="sales_amount", format="money", width=15),
        ],
        group_by=["员工ID"],
        sort_by=[SortRule(field="seq", order="asc")],
        match_key=MatchKey(
            template_fields=["员工ID"],
            data_fields=["销售店员ERPID"],
        ),
        summary_rules=[
            SummaryRule(type="sum", source_field="销售金额", target_field="sales_amount"),
            SummaryRule(type="percentage", source_field="sales_amount", target_field="percentage", base_field="total_sales"),
        ],
        employee_list=[
            EmployeeRow(seq=1, area="渝中", store="保康", name="梅朱琳", employee_id="14694",
                        department="重庆桐君阁-渝中-保康"),
            EmployeeRow(seq=2, area="北碚", store="北碚6店", name="刘敏", employee_id="6653",
                        department="重庆桐君阁-北碚-北碚6店"),
        ],
    )


# ── Analysis result fixtures ──

@pytest.fixture
def mock_analysis_result():
    """A sample AnalysisResult for report testing."""
    rows = [
        AnalysisRow(seq=1, area="渝中", store="保康", name="梅朱琳", employee_id="14694",
                    sales_amount=7981.00, percentage=10.39, department="重庆桐君阁-渝中-保康"),
        AnalysisRow(seq=2, area="北碚", store="北碚6店", name="刘敏", employee_id="6653",
                    sales_amount=148.00, percentage=0.19, department="重庆桐君阁-北碚-北碚6店"),
    ]
    return AnalysisResult(
        template_name="sanzhen-jiuti",
        rows=rows,
        unmatched_rows=[],
        total_row=AnalysisTotal(total_sales=8129.00, total_employees=2, total_stores=2),
        metadata=AnalysisMetadata(
            raw_data_rows=50, template_rows=2, matched_rows=2, unmatched_rows=0,
            match_rate=1.0, elapsed_seconds=0.5,
            date_range=("2026-06-01", "2026-06-16"),
        ),
    )


# ── Helpers ──

def generate_mock_order_data(employee_count=10, seed=42):
    """Generate random order data for testing."""
    import random
    random.seed(seed)
    stores = [f"测试店{i}" for i in range(employee_count)]
    rows = []
    for i in range(employee_count):
        # Generate 1-5 orders per employee
        num_orders = random.randint(1, 5)
        for _ in range(num_orders):
            rows.append({
                "订单号": f"ORD{random.randint(1000, 9999)}",
                "商品ERPID": str(random.randint(100000, 999999)),
                "成本价": round(random.uniform(10, 100), 2),
                "销售单价": round(random.uniform(20, 200), 2),
                "销售数量": random.randint(1, 10),
                "销售金额": round(random.uniform(50, 500), 2),
                "支付时间": "2026-06-05 10:30:00",
                "销售门店ID": f"ST{i:03d}",
                "销售门店": stores[i],
                "销售店员ERPID": str(10000 + i),
                "销售店员姓名": f"测试员工{i}",
            })
    return rows
