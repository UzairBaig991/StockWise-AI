from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from src.data_ingestion import download_template, import_transactions_from_upload
from src.ui_components import page_title

page_title("Data Import", "Upload CSV or Excel sales data and validate the schema before saving it.")

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
if uploaded_file is not None:
    try:
        summary = import_transactions_from_upload(uploaded_file)
        st.success(f"Import batch {summary['batch_id']} saved successfully.")
        st.write("Accepted rows:", summary["counts"]["accepted"])
        st.write("Cancelled rows:", summary["counts"]["cancelled"])
        st.write("Returned rows excluded:", summary["counts"]["returned"])
        st.write("Rejected rows:", summary["counts"]["rejected"])

        if summary["sample_preview"]:
            preview_df = pd.DataFrame(summary["sample_preview"])
            st.subheader("Preview")
            st.dataframe(preview_df.head(10), use_container_width=True)
    except ValueError as exc:
        st.error(str(exc))
        st.markdown(
            """
            Expected columns include one of the following accepted names:
            - InvoiceNo / invoice_no
            - StockCode / product_code
            - InvoiceDate / invoice_date
            - Quantity / quantity
            Optional fields: Description, UnitPrice, CustomerID, Country
            """
        )

st.subheader("Download template")
file_bytes = download_template()
st.download_button("Download CSV template", data=file_bytes, file_name="stockwise_template.csv", mime="text/csv")
