"""Tests for the product data warehouse."""

import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from product_warehouse import (
    generate_product_dimension,
    generate_supplier_dimension,
    generate_inventory_facts,
    ProductWarehouse,
)


class TestProductDimension:
    def test_returns_dataframe(self):
        df = generate_product_dimension(50)
        assert isinstance(df, pd.DataFrame)

    def test_correct_count(self):
        df = generate_product_dimension(75)
        assert len(df) == 75

    def test_has_expected_columns(self):
        df = generate_product_dimension(10)
        expected = ["product_id", "product_name", "category", "brand", "base_price", "is_active"]
        for col in expected:
            assert col in df.columns

    def test_unique_product_ids(self):
        df = generate_product_dimension(100)
        assert df["product_id"].is_unique

    def test_positive_prices(self):
        df = generate_product_dimension(100)
        assert (df["base_price"] > 0).all()

    def test_reproducible(self):
        df1 = generate_product_dimension(50, seed=99)
        df2 = generate_product_dimension(50, seed=99)
        pd.testing.assert_frame_equal(df1, df2)


class TestSupplierDimension:
    def test_returns_dataframe(self):
        df = generate_supplier_dimension()
        assert isinstance(df, pd.DataFrame)

    def test_has_suppliers(self):
        df = generate_supplier_dimension()
        assert len(df) > 0

    def test_unique_supplier_ids(self):
        df = generate_supplier_dimension()
        assert df["supplier_id"].is_unique

    def test_reliability_in_range(self):
        df = generate_supplier_dimension()
        assert (df["reliability_score"] >= 0).all()
        assert (df["reliability_score"] <= 1).all()


class TestInventoryFacts:
    def test_returns_dataframe(self):
        products = generate_product_dimension(20)
        suppliers = generate_supplier_dimension()
        df = generate_inventory_facts(products, suppliers, 100)
        assert isinstance(df, pd.DataFrame)

    def test_correct_count(self):
        products = generate_product_dimension(20)
        suppliers = generate_supplier_dimension()
        df = generate_inventory_facts(products, suppliers, 200)
        assert len(df) == 200

    def test_referential_integrity_products(self):
        products = generate_product_dimension(20)
        suppliers = generate_supplier_dimension()
        df = generate_inventory_facts(products, suppliers, 100)
        valid_ids = set(products["product_id"])
        assert df["product_id"].isin(valid_ids).all()

    def test_referential_integrity_suppliers(self):
        products = generate_product_dimension(20)
        suppliers = generate_supplier_dimension()
        df = generate_inventory_facts(products, suppliers, 100)
        valid_ids = set(suppliers["supplier_id"])
        assert df["supplier_id"].isin(valid_ids).all()

    def test_non_negative_stock(self):
        products = generate_product_dimension(20)
        suppliers = generate_supplier_dimension()
        df = generate_inventory_facts(products, suppliers, 100)
        assert (df["stock_quantity"] >= 0).all()


class TestProductWarehouse:
    def setup_method(self):
        self.wh = ProductWarehouse().build(n_products=50, n_inventory=200)

    def test_build_populates_tables(self):
        assert len(self.wh.dim_products) == 50
        assert len(self.wh.dim_suppliers) > 0
        assert len(self.wh.fact_inventory) == 200

    def test_query_low_stock(self):
        result = self.wh.query_low_stock()
        assert isinstance(result, pd.DataFrame)
        if len(result) > 0:
            assert "product_name" in result.columns
            assert "category" in result.columns

    def test_query_category_inventory(self):
        result = self.wh.query_category_inventory()
        assert isinstance(result, pd.DataFrame)
        assert "category" in result.columns
        assert "total_stock" in result.columns
        assert len(result) > 0

    def test_query_supplier_reliability(self):
        result = self.wh.query_supplier_reliability()
        assert isinstance(result, pd.DataFrame)
        assert "reliability_score" in result.columns
        assert len(result) > 0
