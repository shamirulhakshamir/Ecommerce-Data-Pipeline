"""Tests for the order ETL pipeline."""

import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from order_pipeline import (
    generate_raw_orders,
    clean_orders,
    enrich_orders,
    aggregate_orders,
    run_order_pipeline,
)


class TestGenerateRawOrders:
    def test_returns_dataframe(self):
        df = generate_raw_orders(50)
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self):
        df = generate_raw_orders(50)
        expected = [
            "order_id", "order_date", "customer_id", "category",
            "product_name", "unit_price", "quantity", "payment_method",
            "status", "shipping_city",
        ]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"

    def test_generates_correct_count_plus_duplicates(self):
        df = generate_raw_orders(100)
        # 100 records + 5 duplicates
        assert len(df) == 105

    def test_reproducible_with_seed(self):
        df1 = generate_raw_orders(50, seed=123)
        df2 = generate_raw_orders(50, seed=123)
        pd.testing.assert_frame_equal(df1, df2)

    def test_contains_data_quality_issues(self):
        """Raw data should have some nulls and negative prices (by design)."""
        df = generate_raw_orders(1000)
        has_nulls = df["customer_id"].isna().any()
        has_negatives = (df["unit_price"] < 0).any()
        # At least one of these should be present in 1000 records
        assert has_nulls or has_negatives


class TestCleanOrders:
    def test_removes_duplicates(self):
        raw = generate_raw_orders(100)
        cleaned = clean_orders(raw)
        assert cleaned["order_id"].is_unique

    def test_removes_null_customers(self):
        raw = generate_raw_orders(500)
        cleaned = clean_orders(raw)
        assert cleaned["customer_id"].isna().sum() == 0

    def test_no_negative_prices(self):
        raw = generate_raw_orders(500)
        cleaned = clean_orders(raw)
        assert (cleaned["unit_price"] >= 0).all()

    def test_dates_parsed(self):
        raw = generate_raw_orders(50)
        cleaned = clean_orders(raw)
        assert pd.api.types.is_datetime64_any_dtype(cleaned["order_date"])

    def test_fewer_records_than_raw(self):
        raw = generate_raw_orders(500)
        cleaned = clean_orders(raw)
        assert len(cleaned) < len(raw)


class TestEnrichOrders:
    def test_adds_total_amount(self):
        raw = generate_raw_orders(50)
        cleaned = clean_orders(raw)
        enriched = enrich_orders(cleaned)
        assert "total_amount" in enriched.columns

    def test_total_amount_correct(self):
        raw = generate_raw_orders(50)
        cleaned = clean_orders(raw)
        enriched = enrich_orders(cleaned)
        expected = round(enriched["unit_price"] * enriched["quantity"], 2)
        pd.testing.assert_series_equal(enriched["total_amount"], expected, check_names=False)

    def test_adds_order_month(self):
        raw = generate_raw_orders(50)
        cleaned = clean_orders(raw)
        enriched = enrich_orders(cleaned)
        assert "order_month" in enriched.columns

    def test_adds_is_revenue(self):
        raw = generate_raw_orders(50)
        cleaned = clean_orders(raw)
        enriched = enrich_orders(cleaned)
        assert "is_revenue" in enriched.columns
        assert enriched["is_revenue"].dtype == bool


class TestAggregateOrders:
    def test_returns_expected_keys(self):
        raw = generate_raw_orders(100)
        enriched = enrich_orders(clean_orders(raw))
        result = aggregate_orders(enriched)
        assert "monthly_revenue" in result
        assert "category_summary" in result
        assert "city_summary" in result
        assert "payment_summary" in result

    def test_monthly_revenue_has_data(self):
        raw = generate_raw_orders(100)
        enriched = enrich_orders(clean_orders(raw))
        result = aggregate_orders(enriched)
        assert len(result["monthly_revenue"]) > 0

    def test_category_summary_columns(self):
        raw = generate_raw_orders(100)
        enriched = enrich_orders(clean_orders(raw))
        result = aggregate_orders(enriched)
        cat = result["category_summary"]
        for col in ["category", "total_orders", "total_revenue", "avg_order_value"]:
            assert col in cat.columns


class TestRunOrderPipeline:
    def test_end_to_end(self):
        result = run_order_pipeline(200)
        assert "raw" in result
        assert "cleaned" in result
        assert "summaries" in result
        assert len(result["cleaned"]) > 0
