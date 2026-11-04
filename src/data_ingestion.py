from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.database import ensure_inventory_for_product, ensure_product, save_transaction_batch
from src.preprocessing import aggregate_daily_demand, read_uploaded_file, validate_and_clean_transactions


def import_transactions_from_upload(file) -> dict[str, Any]:
    if file is None:
        raise ValueError("No file was uploaded.")

    path = Path(file.name)
    temp_path = Path.cwd() / "data" / "raw" / f"upload_{path.name}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(file.getvalue())

    frame = read_uploaded_file(temp_path)
    cleaned, counts = validate_and_clean_transactions(frame)

    product_ids: dict[str, int] = {}
    rows_to_insert: list[dict[str, Any]] = []
    for _, row in cleaned.iterrows():
        sku = str(row["product_code"]).strip()
        if sku not in product_ids:
            product_ids[sku] = ensure_product(sku, name=sku, category="Imported", unit_price=float(row.get("unit_price", 0) or 0))
        ensure_inventory_for_product(product_ids[sku], current_stock=0, safety_stock=0, lead_time_days=7)
        rows_to_insert.append(
            {
                "product_id": product_ids[sku],
                "invoice_no": str(row["invoice_no"]),
                "invoice_date": str(row["invoice_date"]),
                "quantity": float(row["quantity"]),
                "unit_price": float(row.get("unit_price", 0) or 0),
                "customer_id": row.get("customer_id"),
                "country": row.get("country"),
            }
        )

    batch_id = save_transaction_batch(rows_to_insert)
    daily = aggregate_daily_demand(cleaned)
    summary = {
        "batch_id": batch_id,
        "rows_inserted": len(rows_to_insert),
        "counts": counts,
        "daily_demand": daily,
        "sample_preview": cleaned.head(10).to_dict(orient="records"),
    }
    return summary


def download_template() -> bytes:
    template = pd.DataFrame(
        {
            "InvoiceNo": ["INV-1001", "INV-1002"],
            "StockCode": ["A100", "B200"],
            "Description": ["Alpha Widget", "Beta Gadget"],
            "Quantity": [12, 8],
            "InvoiceDate": ["2024-01-01", "2024-01-02"],
            "UnitPrice": [8.5, 12.0],
            "CustomerID": [1001, 1002],
            "Country": ["United Kingdom", "United Kingdom"],
        }
    )
    return template.to_csv(index=False).encode("utf-8")
