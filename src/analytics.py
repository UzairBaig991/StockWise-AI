from __future__ import annotations

import pandas as pd


def summarize_sales_overview(transactions_df: pd.DataFrame) -> dict[str, float | int]:
    if transactions_df.empty:
        return {"total_units": 0.0, "total_revenue": 0.0, "unique_products": 0, "avg_order_quantity": 0.0}

    total_units = float(transactions_df["quantity"].sum())
    revenue = float((transactions_df["quantity"] * transactions_df["unit_price"]).sum()) if "unit_price" in transactions_df.columns else 0.0
    unique_products = int(transactions_df["product_code"].nunique())
    avg_order = float(transactions_df["quantity"].mean()) if not transactions_df.empty else 0.0
    return {
        "total_units": total_units,
        "total_revenue": revenue,
        "unique_products": unique_products,
        "avg_order_quantity": avg_order,
    }


def top_products_by_units(daily_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if daily_df.empty:
        return pd.DataFrame(columns=["product_code", "units_sold"])

    summary = daily_df.groupby("product_code", as_index=False)["units_sold"].sum().sort_values("units_sold", ascending=False)
    return summary.head(top_n).reset_index(drop=True)


def compute_movement_indicators(daily_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df.empty:
        return pd.DataFrame(columns=["product_code", "avg_daily_units", "trend", "status"])

    summary = daily_df.groupby("product_code", as_index=False)["units_sold"].agg(avg_daily_units="mean", total_units="sum")
    summary["trend"] = summary["avg_daily_units"]
    summary["status"] = summary["avg_daily_units"].apply(lambda value: "Fast moving" if value >= 10 else "Steady" if value >= 4 else "Slow moving")
    return summary
