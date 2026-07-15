# ecommerce-data-pipeline-poc

E-commerce data pipeline proof-of-concept demonstrating data engineering skills relevant to Coolblue's Data Engineer role.

## Overview

This project implements three core components of a production-grade e-commerce data platform:

1. **Order Pipeline** (`src/order_pipeline.py`) — Full ETL pipeline that extracts raw order data, cleans and enriches it (deduplication, null handling, computed fields), and produces aggregated analytics tables (monthly revenue, category breakdowns, city distribution, payment method analysis).

2. **Product Warehouse** (`src/product_warehouse.py`) — Star-schema dimensional model with product and supplier dimensions plus inventory fact tables. Supports analytical queries: low-stock alerts, category inventory aggregation, and supplier reliability analysis.

3. **Data Quality Framework** (`src/quality_framework.py`) — Reusable validation framework with checks for completeness, uniqueness, value ranges, referential integrity, schema conformance, and data freshness. Produces structured quality reports.

## Tech Stack

- **Python** — Pipeline logic and orchestration
- **Pandas** — Data transformation and analysis
- **pytest** — Automated testing

## Project Structure

```
POC_Project/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── order_pipeline.py        # Order ETL pipeline
│   ├── product_warehouse.py     # Dimensional data warehouse
│   └── quality_framework.py     # Data quality checks
└── tests/
    ├── __init__.py
    ├── test_order_pipeline.py
    ├── test_product_warehouse.py
    └── test_quality_framework.py
```

## Setup

```bash
pip install -r requirements.txt
```

## Run Pipelines

```bash
# Order ETL pipeline
python src/order_pipeline.py

# Product warehouse
python src/product_warehouse.py

# Quality checks
python src/quality_framework.py
```

## Run Tests

```bash
pytest tests/ -v
```

## Key Design Decisions

- **Synthetic data with realistic quality issues** — Raw order data includes nulls, duplicates, and invalid values to demonstrate cleaning capabilities.
- **Star schema** — Product warehouse uses dimensional modeling (dims + facts) for efficient analytical queries.
- **Composable quality checks** — Each check is a standalone function returning structured results, making it easy to build custom validation suites per pipeline.
- **Reproducible** — All data generation uses seeds for deterministic output.

## Author

Shamirul Hak Surbudeen
