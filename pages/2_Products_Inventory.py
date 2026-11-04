import streamlit as st

from src.database import ensure_product, fetch_products, update_inventory
from src.ui_components import page_title

page_title("Products & Inventory", "Maintain product metadata and stock settings for reorder decisions.")

products = fetch_products()
if not products:
    st.info("Add data first from the Data Import page.")
    st.stop()

selected = st.selectbox("Choose a product", [row["sku"] for row in products])
product_row = next(item for item in products if item["sku"] == selected)

with st.form("inventory_form"):
    st.subheader(f"Editing {selected}")
    sku = st.text_input("SKU", value=selected)
    name = st.text_input("Name", value=product_row.get("name") or selected)
    current_stock = st.number_input("Current stock", min_value=0.0, value=float(product_row.get("current_stock", 0) or 0), step=1.0)
    safety_stock = st.number_input("Safety stock", min_value=0.0, value=float(product_row.get("safety_stock", 0) or 0), step=1.0)
    lead_time_days = st.number_input("Lead time (days)", min_value=1, value=int(product_row.get("lead_time_days", 7) or 7), step=1)
    supplier_name = st.text_input("Supplier name", value="")
    submit = st.form_submit_button("Save inventory")

if submit:
    product_id = ensure_product(sku, name=name)
    update_inventory(product_id, current_stock, safety_stock, lead_time_days, supplier_name=supplier_name or None)
    st.success(f"Inventory saved for {sku}.")
    st.rerun()

st.subheader("Product list")
st.dataframe(products, use_container_width=True)
