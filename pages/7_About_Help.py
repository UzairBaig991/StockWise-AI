import streamlit as st

from src.ui_components import page_title

page_title("About & Help", "Project purpose, accepted schema, methodology, and run notes.")

st.markdown(
    """
    ## Project overview
    StockWise AI helps small retail teams import transaction data, clean product-level demand, compare demand forecast models, and combine forecasts with inventory settings to support reorder decisions.

    ## Accepted upload schema
    The importer maps common UCI Online Retail column names to the canonical internal schema.
    Required columns:
    - invoice_no / InvoiceNo
    - product_code / StockCode
    - invoice_date / InvoiceDate
    - quantity / Quantity

    Optional columns include description, unit_price, customer_id, and country.

    ## Methodology
    - Historical demand is aggregated into product/day totals.
    - Invalid dates, cancelled invoices, zero quantities, and missing product codes are excluded or reported.
    - Forecasting uses time-aware lag and rolling features with no leakage from the target day.
    - Reorder logic combines expected lead-time demand and safety stock.

    ## Dataset citation
    UCI Online Retail Data Set. Dua, D. and Graff, C. (2019). UCI Machine Learning Repository.
    https://archive.ics.uci.edu/dataset/352/online+retail

    ## Run instructions
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    streamlit run app.py
    ```
    """
)
