"""
Order Pipeline — ETL for e-commerce order data.

Extracts raw order records, transforms them (cleaning, enrichment, aggregation),
and loads into a structured format ready for analytics.
"""

import pandas as pd
from datetime import datetime, timedelta
import random
import hashlib


# ---------------------------------------------------------------------------
# EXTRACT — Generate synthetic e-commerce order data
# ---------------------------------------------------------------------------
def generate_raw_orders(n_orders: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic raw order data simulating a mid-size e-commerce platform."""
    random.seed(seed)

    categories = ["Laptops", "TVs", "Washing Machines", "Phones", "Headphones",
                  "Tablets", "Refrigerators", "Cameras", "Gaming", "Smart Home"]
    payment_methods = ["iDEAL", "Credit Card", "PayPal", "Bancontact", "Klarna"]
    statuses = ["completed", "completed", "completed", "completed",
                "returned", "cancelled", "pending"]
    cities = ["Rotterdam", "Amsterdam", "Utrecht", "Den Haag", "Eindhoven",
              "Groningen", "Tilburg", "Almere", "Breda", "Nijmegen"]

    base_date = datetime(2024, 1, 1)
    records = []

    for i in range(n_orders):
        order_date = base_date + timedelta(days=random.randint(0, 365))
        category = random.choice(categories)

        # Price ranges by category
        price_ranges = {
            "Laptops": (400, 2500), "TVs": (200, 3000),
            "Washing Machines": (300, 1200), "Phones": (150, 1400),
            "Headphones": (20, 400), "Tablets": (100, 1200),
            "Refrigerators": (250, 1500), "Cameras": (100, 2000),
            "Gaming": (30, 600), "Smart Home": (15, 300),
        }
        lo, hi = price_ranges[category]
        unit_price = round(random.uniform(lo, hi), 2)
        quantity = random.choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]

        # Introduce some data quality issues (nulls, duplicates, bad values)
        customer_id = f"CUST-{random.randint(1000, 9999)}"
        if random.random() < 0.02:
            customer_id = None  # Missing customer
        if random.random() < 0.01:
            unit_price = -unit_price  # Negative price (data error)

        records.append({
            "order_id": f"ORD-{100000 + i}",
            "order_date": order_date.strftime("%Y-%m-%d"),
            "customer_id": customer_id,
            "category": category,
            "product_name": f"{category[:-1] if category.endswith('s') else category} Model-{random.randint(100, 999)}",
            "unit_price": unit_price,
            "quantity": quantity,
            "payment_method": random.choice(payment_methods),
            "status": random.choice(statuses),
            "shipping_city": random.choice(cities),
        })

    # Add a few duplicate rows (data quality issue)
    for _ in range(5):
        records.append(records[random.randint(0, len(records) - 1)].copy())

    df = pd.DataFrame(records)
    return df


# ---------------------------------------------------------------------------
# TRANSFORM — Clean, validate, enrich
# ---------------------------------------------------------------------------
def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw order data: remove duplicates, handle nulls, fix bad values."""
    cleaned = df.copy()

    # Remove exact duplicates
    cleaned = cleaned.drop_duplicates(subset=["order_id"], keep="first")

    # Remove rows with null customer_id
    cleaned = cleaned.dropna(subset=["customer_id"])

    # Fix negative prices (take absolute value)
    cleaned["unit_price"] = cleaned["unit_price"].abs()

    # Ensure quantity is positive
    cleaned = cleaned[cleaned["quantity"] > 0]

    # Parse dates
    cleaned["order_date"] = pd.to_datetime(cleaned["order_date"])

    return cleaned.reset_index(drop=True)


def enrich_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns: total_amount, order_month, revenue_flag."""
    enriched = df.copy()

    enriched["total_amount"] = round(enriched["unit_price"] * enriched["quantity"], 2)
    enriched["order_month"] = enriched["order_date"].dt.to_period("M").astype(str)
    enriched["is_revenue"] = enriched["status"].isin(["completed", "pending"])

    return enriched


# ---------------------------------------------------------------------------
# LOAD — Aggregate for analytics
# ---------------------------------------------------------------------------
def aggregate_orders(df: pd.DataFrame) -> dict:
    """Produce summary tables for downstream analytics / dashboards."""

    # Monthly revenue
    revenue_df = df[df["is_revenue"]].copy()
    monthly_revenue = (
        revenue_df.groupby("order_month")["total_amount"]
        .sum()
        .reset_index()
        .rename(columns={"total_amount": "revenue"})
    )

    # Category breakdown
    category_summary = (
        revenue_df.groupby("category")
        .agg(
            total_orders=("order_id", "count"),
            total_revenue=("total_amount", "sum"),
            avg_order_value=("total_amount", "mean"),
        )
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )

    # City breakdown
    city_summary = (
        revenue_df.groupby("shipping_city")
        .agg(
            total_orders=("order_id", "count"),
            total_revenue=("total_amount", "sum"),
        )
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )

    # Payment method distribution
    payment_summary = (
        revenue_df.groupby("payment_method")["order_id"]
        .count()
        .reset_index()
        .rename(columns={"order_id": "order_count"})
        .sort_values("order_count", ascending=False)
    )

    return {
        "monthly_revenue": monthly_revenue,
        "category_summary": category_summary,
        "city_summary": city_summary,
        "payment_summary": payment_summary,
    }


# ---------------------------------------------------------------------------
# PIPELINE ORCHESTRATOR
# ---------------------------------------------------------------------------
def run_order_pipeline(n_orders: int = 500) -> dict:
    """Execute the full order ETL pipeline: extract -> transform -> load."""
    print("=" * 60)
    print("ORDER PIPELINE — E-commerce Order ETL")
    print("=" * 60)

    # Extract
    print("\n[EXTRACT] Generating raw order data...")
    raw = generate_raw_orders(n_orders)
    print(f"  Raw records: {len(raw)}")

    # Transform
    print("\n[TRANSFORM] Cleaning and enriching...")
    cleaned = clean_orders(raw)
    print(f"  After cleaning: {len(cleaned)} (removed {len(raw) - len(cleaned)} bad records)")
    enriched = enrich_orders(cleaned)

    # Load
    print("\n[LOAD] Aggregating for analytics...")
    summaries = aggregate_orders(enriched)

    print(f"\n  Monthly revenue periods: {len(summaries['monthly_revenue'])}")
    print(f"  Categories tracked: {len(summaries['category_summary'])}")
    print(f"  Cities tracked: {len(summaries['city_summary'])}")

    total_rev = summaries["monthly_revenue"]["revenue"].sum()
    print(f"\n  Total revenue: EUR {total_rev:,.2f}")
    print("\nPipeline complete.")

    return {
        "raw": raw,
        "cleaned": enriched,
        "summaries": summaries,
    }


if __name__ == "__main__":
    result = run_order_pipeline()
