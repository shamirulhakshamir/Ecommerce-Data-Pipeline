"""
Data Quality Framework — Automated validation for e-commerce data pipelines.

Provides reusable quality checks: completeness, uniqueness, range validity,
referential integrity, freshness, and schema conformance.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class QualityCheckResult:
    """Result of a single data quality check."""
    check_name: str
    table_name: str
    passed: bool
    records_checked: int
    records_failed: int
    failure_rate: float
    details: str = ""

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.check_name} on '{self.table_name}': "
            f"{self.records_failed}/{self.records_checked} failed "
            f"({self.failure_rate:.2%}) — {self.details}"
        )


@dataclass
class QualityReport:
    """Aggregated quality report across all checks."""
    results: list = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return len(self.results)

    @property
    def passed_checks(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_checks(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.passed_checks / self.total_checks

    def add(self, result: QualityCheckResult):
        self.results.append(result)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "DATA QUALITY REPORT",
            "=" * 60,
            f"Total checks:  {self.total_checks}",
            f"Passed:        {self.passed_checks}",
            f"Failed:        {self.failed_checks}",
            f"Pass rate:     {self.pass_rate:.1%}",
            "-" * 60,
        ]
        for r in self.results:
            lines.append(str(r))
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# INDIVIDUAL QUALITY CHECKS
# ---------------------------------------------------------------------------

def check_completeness(
    df: pd.DataFrame,
    column: str,
    table_name: str = "unknown",
    threshold: float = 0.95,
) -> QualityCheckResult:
    """Check that a column has no more than (1 - threshold) fraction of nulls."""
    total = len(df)
    nulls = df[column].isna().sum()
    completeness = 1 - (nulls / total) if total > 0 else 0

    return QualityCheckResult(
        check_name=f"completeness({column})",
        table_name=table_name,
        passed=bool(completeness >= threshold),
        records_checked=total,
        records_failed=int(nulls),
        failure_rate=float(nulls / total) if total > 0 else 0.0,
        details=f"completeness={completeness:.3f}, threshold={threshold}",
    )


def check_uniqueness(
    df: pd.DataFrame,
    column: str,
    table_name: str = "unknown",
) -> QualityCheckResult:
    """Check that a column contains only unique values (no duplicates)."""
    total = len(df)
    duplicates = total - df[column].nunique()

    return QualityCheckResult(
        check_name=f"uniqueness({column})",
        table_name=table_name,
        passed=bool(duplicates == 0),
        records_checked=total,
        records_failed=int(duplicates),
        failure_rate=float(duplicates / total) if total > 0 else 0.0,
        details=f"{duplicates} duplicate values found",
    )


def check_value_range(
    df: pd.DataFrame,
    column: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    table_name: str = "unknown",
) -> QualityCheckResult:
    """Check that numeric values fall within an expected range."""
    total = len(df)
    series = df[column]

    if min_val is not None and max_val is not None:
        out_of_range = ((series < min_val) | (series > max_val)).sum()
        detail = f"range=[{min_val}, {max_val}]"
    elif min_val is not None:
        out_of_range = (series < min_val).sum()
        detail = f"min={min_val}"
    elif max_val is not None:
        out_of_range = (series > max_val).sum()
        detail = f"max={max_val}"
    else:
        out_of_range = 0
        detail = "no bounds specified"

    return QualityCheckResult(
        check_name=f"value_range({column})",
        table_name=table_name,
        passed=bool(out_of_range == 0),
        records_checked=total,
        records_failed=int(out_of_range),
        failure_rate=float(out_of_range / total) if total > 0 else 0.0,
        details=f"{out_of_range} out-of-range values; {detail}",
    )


def check_referential_integrity(
    df: pd.DataFrame,
    column: str,
    reference_df: pd.DataFrame,
    reference_column: str,
    table_name: str = "unknown",
) -> QualityCheckResult:
    """Check that all values in column exist in the reference table."""
    total = len(df)
    valid_values = set(reference_df[reference_column].dropna())
    orphans = (~df[column].isin(valid_values)).sum()

    return QualityCheckResult(
        check_name=f"referential_integrity({column})",
        table_name=table_name,
        passed=bool(orphans == 0),
        records_checked=total,
        records_failed=int(orphans),
        failure_rate=float(orphans / total) if total > 0 else 0.0,
        details=f"{orphans} orphan records (not in reference)",
    )


def check_schema(
    df: pd.DataFrame,
    expected_columns: list,
    table_name: str = "unknown",
) -> QualityCheckResult:
    """Check that the DataFrame has all expected columns."""
    actual = set(df.columns)
    expected = set(expected_columns)
    missing = expected - actual

    return QualityCheckResult(
        check_name="schema_check",
        table_name=table_name,
        passed=len(missing) == 0,
        records_checked=len(expected),
        records_failed=len(missing),
        failure_rate=len(missing) / len(expected) if expected else 0,
        details=f"missing columns: {sorted(missing)}" if missing else "all columns present",
    )


def check_freshness(
    df: pd.DataFrame,
    date_column: str,
    max_age_days: int = 7,
    reference_date: Optional[datetime] = None,
    table_name: str = "unknown",
) -> QualityCheckResult:
    """Check that the most recent record is within max_age_days of reference_date."""
    if reference_date is None:
        reference_date = datetime.now()

    dates = pd.to_datetime(df[date_column])
    most_recent = dates.max()
    age_days = (reference_date - most_recent).days

    return QualityCheckResult(
        check_name=f"freshness({date_column})",
        table_name=table_name,
        passed=age_days <= max_age_days,
        records_checked=len(df),
        records_failed=1 if age_days > max_age_days else 0,
        failure_rate=1.0 if age_days > max_age_days else 0.0,
        details=f"most_recent={most_recent.date()}, age={age_days}d, max={max_age_days}d",
    )


# ---------------------------------------------------------------------------
# PIPELINE QUALITY RUNNER
# ---------------------------------------------------------------------------

def run_order_quality_checks(
    orders_df: pd.DataFrame,
    table_name: str = "orders",
) -> QualityReport:
    """Run a standard suite of quality checks on order data."""
    report = QualityReport()

    # Schema
    report.add(check_schema(
        orders_df,
        ["order_id", "order_date", "customer_id", "category",
         "unit_price", "quantity", "status", "shipping_city"],
        table_name,
    ))

    # Completeness
    for col in ["order_id", "customer_id", "order_date", "category"]:
        report.add(check_completeness(orders_df, col, table_name))

    # Uniqueness
    report.add(check_uniqueness(orders_df, "order_id", table_name))

    # Value ranges
    report.add(check_value_range(orders_df, "unit_price", min_val=0, table_name=table_name))
    report.add(check_value_range(orders_df, "quantity", min_val=1, max_val=100, table_name=table_name))

    return report


def run_warehouse_quality_checks(
    products_df: pd.DataFrame,
    suppliers_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
) -> QualityReport:
    """Run quality checks across all warehouse tables."""
    report = QualityReport()

    # Product dimension checks
    report.add(check_schema(
        products_df,
        ["product_id", "product_name", "category", "brand", "base_price", "is_active"],
        "dim_products",
    ))
    report.add(check_uniqueness(products_df, "product_id", "dim_products"))
    report.add(check_completeness(products_df, "product_name", "dim_products"))
    report.add(check_value_range(products_df, "base_price", min_val=0, table_name="dim_products"))

    # Supplier dimension checks
    report.add(check_uniqueness(suppliers_df, "supplier_id", "dim_suppliers"))
    report.add(check_value_range(
        suppliers_df, "reliability_score", min_val=0, max_val=1, table_name="dim_suppliers"
    ))

    # Inventory fact checks — referential integrity
    report.add(check_referential_integrity(
        inventory_df, "product_id", products_df, "product_id", "fact_inventory"
    ))
    report.add(check_referential_integrity(
        inventory_df, "supplier_id", suppliers_df, "supplier_id", "fact_inventory"
    ))
    report.add(check_value_range(
        inventory_df, "stock_quantity", min_val=0, table_name="fact_inventory"
    ))

    return report


if __name__ == "__main__":
    from order_pipeline import generate_raw_orders, clean_orders, enrich_orders
    from product_warehouse import ProductWarehouse

    # Order quality
    raw = generate_raw_orders(500)
    print("\n--- RAW ORDER DATA QUALITY ---")
    raw_report = run_order_quality_checks(raw, "raw_orders")
    print(raw_report.summary())

    cleaned = enrich_orders(clean_orders(raw))
    print("\n--- CLEANED ORDER DATA QUALITY ---")
    clean_report = run_order_quality_checks(cleaned, "cleaned_orders")
    print(clean_report.summary())

    # Warehouse quality
    wh = ProductWarehouse().build()
    print("\n--- WAREHOUSE DATA QUALITY ---")
    wh_report = run_warehouse_quality_checks(
        wh.dim_products, wh.dim_suppliers, wh.fact_inventory
    )
    print(wh_report.summary())
