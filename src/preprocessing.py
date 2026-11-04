from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "invoice_no": {"invoiceno", "invoice no", "invoice_no"},
    "product_code": {"stockcode", "product_code", "productcode", "sku"},
    "invoice_date": {"invoicedate", "invoice date", "invoice_date", "date"},
    "quantity": {"quantity", "qty"},
    "description": {"description", "itemdescription", "product_name", "name"},
    "unit_price": {"unitprice", "unit_price", "price", "unit price"},
    "customer_id": {"customerid", "customer_id", "customer"},
    "country": {"country", "country_code"},
}


def normalize_column_names(columns: list[str]) -> dict[str, str]:
    normalized_map: dict[str, str] = {}
    lower_map = {str(c).strip().lower(): str(c) for c in columns}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                normalized_map[canonical] = lower_map[alias]
                break
    return normalized_map


def read_uploaded_file(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Unsupported file type. Upload CSV or Excel (.xlsx/.xls).")


def validate_and_clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    if df.empty:
        raise ValueError("The uploaded file contains no rows to process.")

    mapping = normalize_column_names(list(df.columns))
    missing = [col for col in ["invoice_no", "product_code", "invoice_date", "quantity"] if col not in mapping]
    if missing:
        accepted = ["InvoiceNo", "StockCode", "InvoiceDate", "Quantity"]
        raise ValueError(
            "Missing required columns. Please include one of the accepted names: "
            f"{accepted}. Missing: {missing}"
        )

    renamed = df.rename(columns={mapping[k]: k for k in mapping})
    renamed["product_code"] = renamed["product_code"].astype(str).str.strip()
    renamed["invoice_no"] = renamed["invoice_no"].astype(str).str.strip()
    renamed["invoice_date"] = pd.to_datetime(renamed["invoice_date"], errors="coerce")

    counts = {
        "total_rows": int(len(renamed)),
        "accepted": 0,
        "rejected": 0,
        "cancelled": 0,
        "returned": 0,
    }

    initial_rows = len(renamed)
    renamed = renamed[renamed["product_code"].notna() & (renamed["product_code"] != "")].copy()
    renamed = renamed[renamed["invoice_date"].notna()].copy()

    counts["rejected"] = initial_rows - len(renamed)

    cancelled_mask = renamed["invoice_no"].astype(str).str.startswith("C")
    counts["cancelled"] = int(cancelled_mask.sum())
    renamed = renamed[~cancelled_mask].copy()

    renamed["quantity"] = pd.to_numeric(renamed["quantity"], errors="coerce")
    renamed = renamed[renamed["quantity"].notna()].copy()
    renamed = renamed[renamed["quantity"] > 0].copy()
    counts["returned"] = int((pd.to_numeric(df.get("quantity"), errors="coerce") < 0).sum()) if "quantity" in df.columns else 0
    counts["accepted"] = int(len(renamed))

    renamed["invoice_date"] = pd.to_datetime(renamed["invoice_date"]).dt.strftime("%Y-%m-%d")
    renamed["description"] = renamed.get("description", pd.Series([None] * len(renamed)))
    renamed["unit_price"] = pd.to_numeric(renamed.get("unit_price", pd.Series([np.nan] * len(renamed))), errors="coerce")
    renamed["customer_id"] = renamed.get("customer_id", pd.Series([None] * len(renamed)))
    renamed["country"] = renamed.get("country", pd.Series([None] * len(renamed)))
    renamed = renamed[["invoice_no", "product_code", "invoice_date", "quantity", "description", "unit_price", "customer_id", "country"]].copy()
    return renamed, counts


def aggregate_daily_demand(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["product_code", "date", "units_sold"])

    daily = (
        df.assign(date=pd.to_datetime(df["invoice_date"]))
        .groupby(["product_code", "date"], as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "units_sold"})
        .sort_values(["product_code", "date"])
        .reset_index(drop=True)
    )
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    return daily


def fill_missing_dates(daily_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df.empty:
        return daily_df

    result = []
    for product_code, group in daily_df.groupby("product_code"):
        start = group["date"].min()
        end = group["date"].max()
        full_index = pd.date_range(start=start, end=end, freq="D")
        full_frame = pd.DataFrame({"date": full_index, "product_code": product_code})
        merged = full_frame.merge(group, on=["product_code", "date"], how="left")
        merged["units_sold"] = merged["units_sold"].fillna(0).astype(float)
        result.append(merged)
    return pd.concat(result, ignore_index=True)


def select_eligible_products(daily_df: pd.DataFrame, min_history_days: int = 14, top_n: int = 15) -> pd.DataFrame:
    if daily_df.empty:
        return pd.DataFrame(columns=["product_code", "history_days", "total_units", "avg_daily_demand"])

    product_stats = (
        daily_df.groupby("product_code")
        .agg(history_days=("date", lambda s: s.nunique()), total_units=("units_sold", "sum"), avg_daily_demand=("units_sold", "mean"))
        .reset_index()
    )
    eligible = product_stats[product_stats["history_days"] >= min_history_days].sort_values(["total_units", "history_days"], ascending=False)
    if top_n:
        eligible = eligible.head(top_n)
    return eligible.reset_index(drop=True)


def prepare_demo_records() -> list[dict[str, Any]]:
    records = [
        {"invoice_no": "INV-1001", "product_code": "A100", "invoice_date": "2024-01-01", "quantity": 12, "description": "Alpha Widget", "unit_price": 8.5, "customer_id": "C001", "country": "US"},
        {"invoice_no": "INV-1002", "product_code": "A100", "invoice_date": "2024-01-02", "quantity": 15, "description": "Alpha Widget", "unit_price": 8.5, "customer_id": "C002", "country": "US"},
        {"invoice_no": "INV-1003", "product_code": "B200", "invoice_date": "2024-01-01", "quantity": 8, "description": "Beta Gadget", "unit_price": 12.0, "customer_id": "C003", "country": "US"},
        {"invoice_no": "INV-1004", "product_code": "B200", "invoice_date": "2024-01-03", "quantity": 10, "description": "Beta Gadget", "unit_price": 12.0, "customer_id": "C004", "country": "US"},
        {"invoice_no": "INV-1005", "product_code": "C300", "invoice_date": "2024-01-02", "quantity": 18, "description": "Gamma Cable", "unit_price": 6.0, "customer_id": "C005", "country": "US"},
        {"invoice_no": "INV-1006", "product_code": "C300", "invoice_date": "2024-01-04", "quantity": 20, "description": "Gamma Cable", "unit_price": 6.0, "customer_id": "C006", "country": "US"},
    ]
    return records
