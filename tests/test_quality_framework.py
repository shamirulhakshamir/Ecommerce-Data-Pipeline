"""Tests for the data quality framework."""

import sys
import os
import pandas as pd
import pytest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quality_framework import (
    QualityCheckResult,
    QualityReport,
    check_completeness,
    check_uniqueness,
    check_value_range,
    check_referential_integrity,
    check_schema,
    check_freshness,
    run_order_quality_checks,
    run_warehouse_quality_checks,
)
from order_pipeline import generate_raw_orders, clean_orders, enrich_orders
from product_warehouse import ProductWarehouse


class TestQualityCheckResult:
    def test_str_pass(self):
        r = QualityCheckResult("test", "tbl", True, 100, 0, 0.0, "ok")
        assert "[PASS]" in str(r)

    def test_str_fail(self):
        r = QualityCheckResult("test", "tbl", False, 100, 10, 0.1, "bad")
        assert "[FAIL]" in str(r)


class TestQualityReport:
    def test_empty_report(self):
        report = QualityReport()
        assert report.total_checks == 0
        assert report.pass_rate == 0.0

    def test_add_results(self):
        report = QualityReport()
        report.add(QualityCheckResult("a", "t", True, 10, 0, 0.0))
        report.add(QualityCheckResult("b", "t", False, 10, 5, 0.5))
        assert report.total_checks == 2
        assert report.passed_checks == 1
        assert report.failed_checks == 1
        assert report.pass_rate == 0.5

    def test_summary_string(self):
        report = QualityReport()
        report.add(QualityCheckResult("a", "t", True, 10, 0, 0.0))
        s = report.summary()
        assert "DATA QUALITY REPORT" in s
        assert "Passed" in s


class TestCheckCompleteness:
    def test_complete_column(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
        result = check_completeness(df, "a")
        assert result.passed is True
        assert result.records_failed == 0

    def test_incomplete_column(self):
        df = pd.DataFrame({"a": [1, None, None, None, None]})
        result = check_completeness(df, "a", threshold=0.95)
        assert result.passed is False

    def test_threshold_boundary(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4, None]})
        result = check_completeness(df, "a", threshold=0.80)
        assert result.passed is True


class TestCheckUniqueness:
    def test_unique_column(self):
        df = pd.DataFrame({"id": [1, 2, 3, 4, 5]})
        result = check_uniqueness(df, "id")
        assert result.passed is True

    def test_duplicate_column(self):
        df = pd.DataFrame({"id": [1, 2, 2, 3, 3]})
        result = check_uniqueness(df, "id")
        assert result.passed is False
        assert result.records_failed == 2


class TestCheckValueRange:
    def test_in_range(self):
        df = pd.DataFrame({"price": [10, 20, 30]})
        result = check_value_range(df, "price", min_val=0, max_val=100)
        assert result.passed is True

    def test_out_of_range_min(self):
        df = pd.DataFrame({"price": [-5, 10, 20]})
        result = check_value_range(df, "price", min_val=0)
        assert result.passed is False
        assert result.records_failed == 1

    def test_out_of_range_max(self):
        df = pd.DataFrame({"price": [10, 20, 200]})
        result = check_value_range(df, "price", max_val=100)
        assert result.passed is False

    def test_no_bounds(self):
        df = pd.DataFrame({"price": [10, 20, 30]})
        result = check_value_range(df, "price")
        assert result.passed is True


class TestCheckReferentialIntegrity:
    def test_valid_references(self):
        df = pd.DataFrame({"product_id": ["A", "B", "C"]})
        ref = pd.DataFrame({"product_id": ["A", "B", "C", "D"]})
        result = check_referential_integrity(df, "product_id", ref, "product_id")
        assert result.passed is True

    def test_orphan_records(self):
        df = pd.DataFrame({"product_id": ["A", "B", "X"]})
        ref = pd.DataFrame({"product_id": ["A", "B", "C"]})
        result = check_referential_integrity(df, "product_id", ref, "product_id")
        assert result.passed is False
        assert result.records_failed == 1


class TestCheckSchema:
    def test_all_columns_present(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        result = check_schema(df, ["a", "b", "c"])
        assert result.passed is True

    def test_missing_columns(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        result = check_schema(df, ["a", "b", "c"])
        assert result.passed is False
        assert result.records_failed == 1


class TestCheckFreshness:
    def test_fresh_data(self):
        df = pd.DataFrame({"date": ["2024-12-20"]})
        ref = datetime(2024, 12, 21)
        result = check_freshness(df, "date", max_age_days=7, reference_date=ref)
        assert result.passed is True

    def test_stale_data(self):
        df = pd.DataFrame({"date": ["2024-01-01"]})
        ref = datetime(2024, 12, 31)
        result = check_freshness(df, "date", max_age_days=7, reference_date=ref)
        assert result.passed is False


class TestRunOrderQualityChecks:
    def test_raw_data_has_failures(self):
        raw = generate_raw_orders(500)
        report = run_order_quality_checks(raw, "raw_orders")
        assert report.total_checks > 0
        # Raw data should have some quality issues
        assert report.failed_checks > 0

    def test_cleaned_data_passes_more(self):
        raw = generate_raw_orders(500)
        cleaned = enrich_orders(clean_orders(raw))
        report = run_order_quality_checks(cleaned, "cleaned_orders")
        assert report.total_checks > 0
        assert report.pass_rate > 0.8


class TestRunWarehouseQualityChecks:
    def test_warehouse_quality(self):
        wh = ProductWarehouse().build(n_products=50, n_inventory=200)
        report = run_warehouse_quality_checks(
            wh.dim_products, wh.dim_suppliers, wh.fact_inventory
        )
        assert report.total_checks > 0
        # Warehouse data is generated clean, should pass all checks
        assert report.pass_rate == 1.0
