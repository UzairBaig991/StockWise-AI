import pandas as pd

from src.preprocessing import validate_and_clean_transactions


def test_validate_and_clean_transactions_accepts_uplifted_records():
    df = pd.DataFrame(
        {
            "InvoiceNo": ["INV-1", "CINV-2", "INV-3"],
            "StockCode": ["A100", "B200", "A100"],
            "InvoiceDate": ["2024-01-01", "2024-01-02", "bad-date"],
            "Quantity": [5, 3, 7],
        }
    )

    cleaned, counts = validate_and_clean_transactions(df)
    assert counts["accepted"] == 1
    assert cleaned.iloc[0]["product_code"] == "A100"
    assert cleaned["invoice_date"].iloc[0] == "2024-01-01"
