"""
Product Warehouse — Dimensional model for e-commerce product data.

Implements a star-schema-style warehouse with dimension and fact tables
for product catalog, inventory, and supplier data.
"""

import pandas as pd
from datetime import datetime, timedelta
import random


# ---------------------------------------------------------------------------
# DIMENSION: Products
# ---------------------------------------------------------------------------
def generate_product_dimension(n_products: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generate a product dimension table with catalog attributes."""
    random.seed(seed)

    categories = {
        "Laptops": ["Dell", "HP", "Lenovo", "ASUS", "Acer"],
        "TVs": ["Samsung", "LG", "Sony", "Philips", "Panasonic"],
        "Phones": ["Apple", "Samsung", "Google", "OnePlus", "Xiaomi"],
        "Headphones": ["Sony", "Bose", "JBL", "Sennheiser", "AKG"],
        "Tablets": ["Apple", "Samsung", "Lenovo", "Microsoft", "Huawei"],
        "Washing Machines": ["Bosch", "Miele", "Samsung", "Siemens", "AEG"],
        "Refrigerators": ["Bosch", "Samsung", "LG", "Liebherr", "Miele"],
        "Gaming": ["Sony", "Microsoft", "Nintendo", "Razer", "Logitech"],
        "Cameras": ["Canon", "Nikon", "Sony", "Fujifilm", "Panasonic"],
        "Smart Home": ["Philips Hue", "Google", "Amazon", "Ring", "Tado"],
    }

    records = []
    for i in range(n_products):
        category = random.choice(list(categories.keys()))
        brand = random.choice(categories[category])

        price_ranges = {
            "Laptops": (400, 2500), "TVs": (200, 3000),
            "Phones": (150, 1400), "Headphones": (20, 400),
            "Tablets": (100, 1200), "Washing Machines": (300, 1200),
            "Refrigerators": (250, 1500), "Gaming": (30, 600),
            "Cameras": (100, 2000), "Smart Home": (15, 300),
        }
        lo, hi = price_ranges[category]

        records.append({
            "product_id": f"PROD-{1000 + i}",
            "product_name": f"{brand} {category[:-1] if category.endswith('s') else category} {random.randint(100, 999)}",
            "category": category,
            "brand": brand,
            "base_price": round(random.uniform(lo, hi), 2),
            "weight_kg": round(random.uniform(0.1, 30.0), 2),
            "is_active": random.random() > 0.1,
            "created_date": (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d"),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# DIMENSION: Suppliers
# ---------------------------------------------------------------------------
def generate_supplier_dimension(seed: int = 42) -> pd.DataFrame:
    """Generate a supplier dimension table."""
    random.seed(seed)

    suppliers = [
        {"supplier_id": "SUP-001", "name": "TechDistro BV", "country": "Netherlands", "reliability_score": 0.95},
        {"supplier_id": "SUP-002", "name": "ElectroWholesale GmbH", "country": "Germany", "reliability_score": 0.92},
        {"supplier_id": "SUP-003", "name": "Nordic Electronics AB", "country": "Sweden", "reliability_score": 0.88},
        {"supplier_id": "SUP-004", "name": "EuroTech SRL", "country": "Italy", "reliability_score": 0.85},
        {"supplier_id": "SUP-005", "name": "BritParts Ltd", "country": "United Kingdom", "reliability_score": 0.90},
        {"supplier_id": "SUP-006", "name": "AsiaLink Trading", "country": "China", "reliability_score": 0.82},
        {"supplier_id": "SUP-007", "name": "FranceTech SARL", "country": "France", "reliability_score": 0.87},
    ]

    return pd.DataFrame(suppliers)


# ---------------------------------------------------------------------------
# FACT: Inventory Snapshots
# ---------------------------------------------------------------------------
def generate_inventory_facts(
    products: pd.DataFrame,
    suppliers: pd.DataFrame,
    n_records: int = 500,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate fact table: daily inventory snapshots linking products to suppliers."""
    random.seed(seed)

    product_ids = products["product_id"].tolist()
    supplier_ids = suppliers["supplier_id"].tolist()

    records = []
    base_date = datetime(2024, 1, 1)

    for i in range(n_records):
        snapshot_date = base_date + timedelta(days=random.randint(0, 90))
        product_id = random.choice(product_ids)
        supplier_id = random.choice(supplier_ids)

        records.append({
            "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
            "product_id": product_id,
            "supplier_id": supplier_id,
            "stock_quantity": random.randint(0, 500),
            "reorder_point": random.randint(10, 50),
            "lead_time_days": random.randint(1, 14),
            "unit_cost": round(random.uniform(5.0, 800.0), 2),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# WAREHOUSE BUILDER
# ---------------------------------------------------------------------------
class ProductWarehouse:
    """Star-schema product data warehouse with dimensions and facts."""

    def __init__(self):
        self.dim_products: pd.DataFrame = pd.DataFrame()
        self.dim_suppliers: pd.DataFrame = pd.DataFrame()
        self.fact_inventory: pd.DataFrame = pd.DataFrame()

    def build(self, n_products: int = 100, n_inventory: int = 500, seed: int = 42):
        """Build all dimension and fact tables."""
        print("=" * 60)
        print("PRODUCT WAREHOUSE — Dimensional Model Builder")
        print("=" * 60)

        print("\n[DIM] Building product dimension...")
        self.dim_products = generate_product_dimension(n_products, seed)
        print(f"  Products: {len(self.dim_products)}")
        print(f"  Categories: {self.dim_products['category'].nunique()}")
        print(f"  Brands: {self.dim_products['brand'].nunique()}")

        print("\n[DIM] Building supplier dimension...")
        self.dim_suppliers = generate_supplier_dimension(seed)
        print(f"  Suppliers: {len(self.dim_suppliers)}")

        print("\n[FACT] Building inventory facts...")
        self.fact_inventory = generate_inventory_facts(
            self.dim_products, self.dim_suppliers, n_inventory, seed
        )
        print(f"  Inventory snapshots: {len(self.fact_inventory)}")

        return self

    def query_low_stock(self, threshold: int = 20) -> pd.DataFrame:
        """Find products below reorder point — useful for supply chain alerts."""
        low = self.fact_inventory[
            self.fact_inventory["stock_quantity"] < self.fact_inventory["reorder_point"]
        ].copy()

        if low.empty:
            return low

        merged = low.merge(
            self.dim_products[["product_id", "product_name", "category", "brand"]],
            on="product_id",
            how="left",
        )
        return merged.sort_values("stock_quantity")

    def query_category_inventory(self) -> pd.DataFrame:
        """Aggregate inventory by product category."""
        merged = self.fact_inventory.merge(
            self.dim_products[["product_id", "category"]],
            on="product_id",
            how="left",
        )
        return (
            merged.groupby("category")
            .agg(
                total_stock=("stock_quantity", "sum"),
                avg_stock=("stock_quantity", "mean"),
                n_snapshots=("stock_quantity", "count"),
            )
            .reset_index()
            .sort_values("total_stock", ascending=False)
        )

    def query_supplier_reliability(self) -> pd.DataFrame:
        """Join supplier dimension with inventory facts for supply chain analysis."""
        merged = self.fact_inventory.merge(
            self.dim_suppliers, on="supplier_id", how="left"
        )
        return (
            merged.groupby(["supplier_id", "name", "country", "reliability_score"])
            .agg(
                total_supplied=("stock_quantity", "sum"),
                avg_lead_time=("lead_time_days", "mean"),
            )
            .reset_index()
            .sort_values("reliability_score", ascending=False)
        )


if __name__ == "__main__":
    wh = ProductWarehouse().build()

    print("\n--- Low Stock Alert ---")
    low_stock = wh.query_low_stock()
    print(low_stock.head(10).to_string(index=False))

    print("\n--- Category Inventory ---")
    cat_inv = wh.query_category_inventory()
    print(cat_inv.to_string(index=False))

    print("\n--- Supplier Reliability ---")
    sup_rel = wh.query_supplier_reliability()
    print(sup_rel.to_string(index=False))
