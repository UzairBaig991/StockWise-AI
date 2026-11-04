import pandas as pd
import streamlit as st

from src.database import fetch_inventory_rows, get_connection
from src.inventory_logic import compute_reorder_metrics, explain_reorder_reason
from src.ui_components import metric_card, page_title

page_title("Reorder Recommendations", "Review products requiring replenishment based on demand, safety stock, and lead time.")

inventory_rows = fetch_inventory_rows()
if not inventory_rows:
    st.info("Add product inventory data from the Products & Inventory page.")
    st.stop()

with get_connection() as conn:
    sales = conn.execute(
        """
        SELECT p.sku, st.invoice_date, SUM(st.quantity) AS units_sold
        FROM sales_transactions st
        JOIN products p ON p.product_id = st.product_id
        GROUP BY p.sku, st.invoice_date
        ORDER BY st.invoice_date
        """
    ).fetchall()

sales_df = pd.DataFrame(sales, columns=["sku", "invoice_date", "units_sold"])
product_daily = sales_df.groupby("sku")["units_sold"].mean().to_dict() if not sales_df.empty else {}
rows = []
for item in inventory_rows:
    sku = item["sku"]
    mean_daily = float(product_daily.get(sku, 0.0))
    metrics = compute_reorder_metrics(float(item.get("current_stock", 0) or 0), float(item.get("safety_stock", 0) or 0), int(item.get("lead_time_days", 7) or 7), mean_daily)
    rows.append({
        "sku": sku,
        "name": item.get("name"),
        "current_stock": float(item.get("current_stock", 0) or 0),
        "safety_stock": float(item.get("safety_stock", 0) or 0),
        "lead_time_days": int(item.get("lead_time_days", 7) or 7),
        "expected_demand_during_lead_time": float(metrics["expected_demand_during_lead_time"]),
        "reorder_point": float(metrics["reorder_point"]),
        "recommended_order_qty": float(metrics["recommended_order_qty"]),
        "needs_review": bool(metrics["needs_review"]),
        "reason": explain_reorder_reason(metrics, int(item.get("lead_time_days", 7) or 7)),
    })

results = pd.DataFrame(rows)
if results.empty:
    st.info("No reorder recommendations available.")
    st.stop()

results = results.sort_values(["needs_review", "recommended_order_qty"], ascending=[False, False]).reset_index(drop=True)
show_all = st.checkbox("Show all products", value=True)
if not show_all:
    results = results[results["needs_review"]].reset_index(drop=True)

risk_count = int(results["needs_review"].sum())
order_volume = float(results["recommended_order_qty"].sum())
avg_reorder = float(results["recommended_order_qty"].mean()) if not results.empty else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    metric_card("At-risk items", str(risk_count), "products to review")
with col2:
    metric_card("Recommended units", f"{order_volume:,.0f}", "total suggested order quantity")
with col3:
    metric_card("Avg order qty", f"{avg_reorder:,.1f}", "per reviewed item")

st.subheader("Recommendation summary")
summary_by_status = results.groupby("needs_review").size().rename(index={True: "Needs review", False: "Healthy"})
st.dataframe(summary_by_status.rename("count").to_frame(), use_container_width=True)

csv_bytes = results.to_csv(index=False).encode("utf-8")
st.download_button(
    "Export recommendations as CSV",
    data=csv_bytes,
    file_name="stockwise_reorder_recommendations.csv",
    mime="text/csv",
)

st.subheader("Priority list")
st.dataframe(results, use_container_width=True)

with st.expander("Reason summary"):
    for _, row in results.iterrows():
        st.markdown(f"- **{row['sku']}**: {row['reason']}")
