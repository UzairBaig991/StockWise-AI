import json

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics_export import build_analytics_export
from src.database import fetch_inventory_rows, fetch_model_runs, get_connection
from src.inventory_logic import compute_reorder_metrics
from src.ui_components import metric_card, page_title

page_title("Sales Analytics", "Explore demand patterns and export a complete analytics package.")

with get_connection() as conn:
    sales_rows = conn.execute(
        """
        SELECT p.sku, st.invoice_date, SUM(st.quantity) AS units_sold
        FROM sales_transactions st
        JOIN products p ON p.product_id = st.product_id
        GROUP BY p.sku, st.invoice_date
        ORDER BY st.invoice_date
        """
    ).fetchall()

if not sales_rows:
    st.info("Upload data first to view and export sales analytics.")
    st.stop()

sales = pd.DataFrame(sales_rows)
sales["invoice_date"] = pd.to_datetime(sales["invoice_date"])
products = sorted(sales["sku"].unique().tolist())

with st.container(border=True):
    st.subheader("Analysis filters")
    product_filter = st.multiselect(
        "Products",
        products,
        default=products[: min(5, len(products))],
    )
    date_columns = st.columns(2)
    with date_columns[0]:
        start_date = st.date_input("Start date", value=sales["invoice_date"].min().date())
    with date_columns[1]:
        end_date = st.date_input("End date", value=sales["invoice_date"].max().date())
    display_columns = st.columns(2)
    with display_columns[0]:
        aggregation = st.selectbox("Chart interval", ["Daily", "Weekly", "Monthly"])
    with display_columns[1]:
        show_rolling = st.checkbox("Show 7-period rolling average", value=False)

if start_date > end_date:
    st.error("Start date must be on or before end date.")
    st.stop()
if not product_filter:
    st.info("Select at least one product to display analytics.")
    st.stop()

filtered = sales[
    sales["sku"].isin(product_filter)
    & (sales["invoice_date"].dt.date >= start_date)
    & (sales["invoice_date"].dt.date <= end_date)
].copy()
if filtered.empty:
    st.warning("No sales match the selected products and date range.")
    st.stop()

total_units = float(filtered["units_sold"].sum())
average_daily = float(filtered.groupby("invoice_date")["units_sold"].sum().mean())
daily_totals = filtered.groupby("sku")["units_sold"].sum().sort_values(ascending=False)
peak_sku = str(daily_totals.index[0])

kpi_columns = st.columns(4)
with kpi_columns[0]:
    metric_card("Selected units", f"{total_units:,.0f}", "filtered period")
with kpi_columns[1]:
    metric_card("Avg. daily demand", f"{average_daily:,.1f}", "units per observed day")
with kpi_columns[2]:
    metric_card("Products", str(filtered["sku"].nunique()), "in current view")
with kpi_columns[3]:
    metric_card("Top product", peak_sku, f"{daily_totals.iloc[0]:,.0f} units")

chart_data = filtered.copy()
if aggregation == "Weekly":
    chart_data["period"] = chart_data["invoice_date"].dt.to_period("W").dt.start_time
elif aggregation == "Monthly":
    chart_data["period"] = chart_data["invoice_date"].dt.to_period("M").dt.start_time
else:
    chart_data["period"] = chart_data["invoice_date"]

trend = (
    chart_data.groupby(["sku", "period"], as_index=False)["units_sold"]
    .sum()
    .sort_values(["sku", "period"])
)
if show_rolling:
    trend["rolling_average"] = trend.groupby("sku")["units_sold"].transform(
        lambda values: values.rolling(window=7, min_periods=1).mean()
    )
    trend_long = trend.melt(
        id_vars=["sku", "period"],
        value_vars=["units_sold", "rolling_average"],
        var_name="measure",
        value_name="units",
    )
    chart = px.line(
        trend_long,
        x="period",
        y="units",
        color="sku",
        line_dash="measure",
        title=f"{aggregation} demand and rolling average",
        labels={"period": "Date", "units": "Units sold", "sku": "Product"},
    )
else:
    chart = px.line(
        trend,
        x="period",
        y="units_sold",
        color="sku",
        title=f"{aggregation} demand",
        labels={"period": "Date", "units_sold": "Units sold", "sku": "Product"},
    )
st.plotly_chart(chart, use_container_width=True)

product_summary = (
    filtered.groupby("sku", as_index=False)
    .agg(total_units=("units_sold", "sum"), average_daily_units=("units_sold", "mean"), active_days=("invoice_date", "nunique"))
    .sort_values("total_units", ascending=False)
)
st.subheader("Product demand summary")
st.dataframe(product_summary, use_container_width=True, hide_index=True)

st.subheader("Export all analytics")
st.caption(
    "Downloads a ZIP containing the current filtered sales data and summaries, plus inventory recommendations "
    "and recent model evaluation history."
)

inventory_rows = fetch_inventory_rows()
inventory_frame = pd.DataFrame(inventory_rows)
if not inventory_frame.empty:
    overall_daily_demand = sales.groupby("sku")["units_sold"].mean().to_dict()
    reorder_rows = []
    for item in inventory_rows:
        daily_demand = float(overall_daily_demand.get(item["sku"], 0.0))
        metrics = compute_reorder_metrics(
            current_stock=float(item.get("current_stock") or 0),
            safety_stock=float(item.get("safety_stock") or 0),
            lead_time_days=int(item.get("lead_time_days") or 7),
            daily_demand=daily_demand,
            review_period_days=int(item.get("reorder_target_days") or 7),
        )
        reorder_rows.append(
            {
                **item,
                "average_daily_demand": daily_demand,
                **metrics,
            }
        )
    recommendations = pd.DataFrame(reorder_rows)
else:
    recommendations = pd.DataFrame()

model_history = pd.DataFrame(fetch_model_runs(limit=100))
if not model_history.empty and "metadata_json" in model_history.columns:
    model_history["metadata_json"] = model_history["metadata_json"].map(
        lambda value: json.dumps(value, sort_keys=True, default=str)
        if isinstance(value, dict)
        else "{}"
    )

export_tables = {
    "filtered_sales": filtered.assign(invoice_date=filtered["invoice_date"].dt.strftime("%Y-%m-%d")),
    "product_summary": product_summary,
    "demand_trend": trend,
    "inventory_settings": inventory_frame,
    "reorder_recommendations": recommendations,
    "model_run_history": model_history,
}
archive_bytes = build_analytics_export(export_tables)
st.download_button(
    "Download all analytics (ZIP)",
    data=archive_bytes,
    file_name="stockwise_analytics_export.zip",
    mime="application/zip",
    type="primary",
)
