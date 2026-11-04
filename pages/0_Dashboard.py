from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import fetch_inventory_rows, fetch_products, get_connection
from src.inventory_logic import compute_reorder_metrics
from src.ui_components import metric_card, page_title

page_title("Dashboard", "A clear view of your inventory, demand, and next actions.")

header_left, header_right = st.columns([1, 0.25], vertical_alignment="center")
with header_left:
    st.markdown(
        '<span class="sw-live"><span class="sw-live-dot"></span>Connected to your inventory</span>',
        unsafe_allow_html=True,
    )
with header_right:
    if st.button("↻  Refresh", use_container_width=True):
        st.rerun()

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
    activity_rows = conn.execute(
        """
        SELECT p.sku, st.invoice_no, st.invoice_date, st.quantity
        FROM sales_transactions st
        JOIN products p ON p.product_id = st.product_id
        ORDER BY st.created_at DESC, st.transaction_id DESC
        LIMIT 8
        """
    ).fetchall()

products = fetch_products()
inventory_rows = fetch_inventory_rows()
sales = pd.DataFrame(sales_rows, columns=["sku", "invoice_date", "units_sold"])
activity = pd.DataFrame(
    activity_rows,
    columns=["sku", "invoice_no", "invoice_date", "quantity"],
)

if not sales.empty:
    sales["invoice_date"] = pd.to_datetime(sales["invoice_date"])
    data_end = sales["invoice_date"].max().normalize()
    data_start = sales["invoice_date"].min().normalize()
    product_daily_demand = sales.groupby("sku")["units_sold"].mean().to_dict()
else:
    data_end = None
    data_start = None
    product_daily_demand = {}

window_column, product_column = st.columns(2)
with window_column:
    selected_window = st.selectbox(
        "Sales period",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All available data"],
        index=1,
        key="dashboard_sales_window",
    )
with product_column:
    product_options = ["All products", *sorted(sales["sku"].astype(str).unique())] if not sales.empty else ["All products"]
    selected_product = st.selectbox(
        "Product trend",
        product_options,
        key="dashboard_product_filter",
        disabled=sales.empty,
    )

period_days = {
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
}.get(selected_window)
comparison_sales = (
    sales[sales["sku"] == selected_product]
    if selected_product != "All products"
    else sales
)
if data_end is not None and data_start is not None:
    current_period_start = (
        max(data_start, data_end - pd.Timedelta(days=period_days - 1))
        if period_days is not None
        else data_start
    )
    current_sales = sales[sales["invoice_date"] >= current_period_start]
    actual_period_days = max(1, (data_end - current_period_start).days + 1)
    if period_days is not None:
        previous_period_end = current_period_start - pd.Timedelta(days=1)
        previous_period_start = previous_period_end - pd.Timedelta(days=period_days - 1)
        if not comparison_sales.empty and comparison_sales["invoice_date"].min() <= previous_period_start:
            previous_sales = comparison_sales[
                (comparison_sales["invoice_date"] >= previous_period_start)
                & (comparison_sales["invoice_date"] <= previous_period_end)
            ]
        else:
            previous_sales = comparison_sales.iloc[0:0]
    else:
        previous_sales = sales.iloc[0:0]
else:
    current_period_start = None
    current_sales = sales
    previous_sales = sales.iloc[0:0]
    actual_period_days = 1

if selected_product != "All products":
    current_sales = current_sales[current_sales["sku"] == selected_product]
    previous_sales = previous_sales[previous_sales["sku"] == selected_product]

current_units = float(current_sales["units_sold"].sum()) if not current_sales.empty else 0.0
previous_units = float(previous_sales["units_sold"].sum()) if not previous_sales.empty else 0.0
if not previous_sales.empty and previous_units > 0:
    sales_delta = f"{(current_units - previous_units) / previous_units:+.1%} vs previous period"
elif period_days is None:
    sales_delta = "All available sales history"
elif period_days is not None and not comparison_sales.empty and comparison_sales["invoice_date"].min() > previous_period_start:
    sales_delta = "Not enough history to compare"
elif current_units > 0:
    sales_delta = f"+{current_units:,.0f} units vs previous period"
else:
    sales_delta = "No sales in selected period"

on_hand_units = sum(float(item.get("current_stock") or 0) for item in inventory_rows)
review_items: list[dict[str, object]] = []
if not sales.empty:
    for item in inventory_rows:
        metrics = compute_reorder_metrics(
            current_stock=float(item.get("current_stock") or 0),
            safety_stock=float(item.get("safety_stock") or 0),
            lead_time_days=int(item.get("lead_time_days") or 7),
            daily_demand=float(product_daily_demand.get(item["sku"], 0.0)),
        )
        if metrics["needs_review"]:
            review_items.append(
                {
                    "sku": item["sku"],
                    "name": item.get("name") or item["sku"],
                    "current_stock": float(item.get("current_stock") or 0),
                    "reorder_point": float(metrics["reorder_point"]),
                    "recommended_order_qty": float(metrics["recommended_order_qty"]),
                }
            )
review_items.sort(key=lambda item: float(item["recommended_order_qty"]), reverse=True)

if not sales.empty and inventory_rows:
    health_score: int | None = round(
        100 * (len(inventory_rows) - len(review_items)) / len(inventory_rows)
    )
else:
    health_score = None

stock_panel, metrics_panel = st.columns([1.08, 1.12], gap="medium")
with stock_panel:
    score = health_score or 0
    score_label = f"{health_score}%" if health_score is not None else "—"
    if health_score is not None:
        health_caption = (
            f"{len(inventory_rows) - len(review_items)} of {len(inventory_rows)} stocked products are above their reorder point."
        )
    elif not sales.empty:
        health_caption = "Add current stock levels to calculate inventory health."
    else:
        health_caption = "Import sales and configure stock to calculate inventory health."
    st.markdown(
        f"""
        <div class="sw-panel">
            <div class="sw-panel-title">Stock health</div>
            <div class="sw-panel-caption">Reorder risk across tracked inventory</div>
            <div class="sw-health">
                <div class="sw-health-ring" style="--health-score:{score}%">
                    <div class="sw-health-ring-inner">
                        <div class="sw-health-score">{score_label}</div>
                        <div class="sw-health-percent">HEALTH</div>
                    </div>
                </div>
                <div>
                    <div class="sw-panel-title">{len(products):,} products tracked</div>
                    <div class="sw-panel-caption">{health_caption}</div>
                    <div style="height:0.65rem"></div>
                    <div class="sw-live"><span class="sw-live-dot"></span>Live inventory status</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metrics_panel:
    metric_top = st.columns(2, gap="small")
    with metric_top[0]:
        metric_card("Total products", f"{len(products):,}", "in your catalog")
    with metric_top[1]:
        metric_card("Units sold", f"{current_units:,.0f}", sales_delta)
    metric_bottom = st.columns(2, gap="small")
    with metric_bottom[0]:
        daily_average = current_units / actual_period_days
        metric_card("Avg. daily demand", f"{daily_average:,.1f}", "units per calendar day")
    with metric_bottom[1]:
        metric_card(
            "Reorder alerts",
            f"{len(review_items):,}" if not sales.empty and inventory_rows else "—",
            (
                "products at or below reorder point"
                if not sales.empty and inventory_rows
                else "configure stock to calculate"
                if not inventory_rows
                else "import sales to calculate"
            ),
        )

st.write("")
if review_items:
    alert_left, alert_right = st.columns([1, 0.22], vertical_alignment="center")
    with alert_left:
        st.markdown(
            f"""
            <div class="sw-alert">
                <div class="sw-alert-icon">!</div>
                <div>
                    <div class="sw-alert-title">{len(review_items)} product{'s' if len(review_items) != 1 else ''} need a stock review</div>
                    <div class="sw-alert-caption">Review reorder quantities before your next replenishment cycle.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with alert_right:
        st.page_link(
            "pages/5_Reorder_Recommendations.py",
            label="Review alerts",
            icon=":material/arrow_forward:",
            use_container_width=True,
        )
elif not sales.empty and inventory_rows:
    st.markdown(
        """
        <div class="sw-alert" style="border-color:rgba(139,226,63,.25);background:rgba(139,226,63,.06)">
            <div class="sw-alert-icon" style="color:#8be23f;border-color:rgba(139,226,63,.35)">✓</div>
            <div>
                <div class="sw-alert-title" style="color:#b5ed8c">Inventory is looking good</div>
                <div class="sw-alert-caption">No configured products are currently below their reorder point.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
elif sales.empty:
    st.markdown(
        """
        <div class="sw-alert">
            <div class="sw-alert-icon">↑</div>
            <div>
                <div class="sw-alert-title">Your dashboard is ready for sales data</div>
                <div class="sw-alert-caption">Import a CSV or Excel file to unlock demand trends and reorder insights.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/1_Data_Import.py",
        label="Import sales data",
        icon=":material/upload_file:",
        use_container_width=False,
    )
else:
    st.markdown(
        """
        <div class="sw-alert">
            <div class="sw-alert-icon">+</div>
            <div>
                <div class="sw-alert-title">Sales data is connected</div>
                <div class="sw-alert-caption">Add current stock and safety-stock levels to calculate reorder insights.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/2_Products_Inventory.py",
        label="Configure inventory",
        icon=":material/inventory_2:",
        use_container_width=False,
    )

st.write("")
chart_panel, activity_panel = st.columns([1.25, 0.75], gap="medium")
with chart_panel:
    with st.container(border=True):
        st.markdown(
            '<div class="sw-panel-title">Demand trend</div>'
            f'<div class="sw-panel-caption">{selected_window} · {selected_product}</div>',
            unsafe_allow_html=True,
        )
        if not current_sales.empty:
            trend = (
                current_sales.groupby("invoice_date", as_index=False)["units_sold"]
                .sum()
                .sort_values("invoice_date")
            )
            chart = px.area(
                trend,
                x="invoice_date",
                y="units_sold",
                template="plotly_dark",
                labels={"invoice_date": "Date", "units_sold": "Units sold"},
            )
            chart.update_traces(
                line_color="#8be23f",
                fillcolor="rgba(139, 226, 63, 0.12)",
            )
            chart.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#b8b8c2",
                margin=dict(l=0, r=0, t=16, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#2b2b32", rangemode="tozero"),
                showlegend=False,
                height=270,
            )
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.markdown(
                '<div class="sw-empty">No sales match this view yet. Try another period or import more sales data.</div>',
                unsafe_allow_html=True,
            )

with activity_panel:
    with st.container(border=True):
        st.markdown(
            '<div class="sw-panel-title">Recent sales</div>'
            '<div class="sw-panel-caption">Latest imported transactions</div>',
            unsafe_allow_html=True,
        )
        if not activity.empty:
            activity["invoice_date"] = pd.to_datetime(activity["invoice_date"]).dt.strftime("%b %d, %Y")
            activity = activity.rename(
                columns={
                    "sku": "Product",
                    "invoice_no": "Invoice",
                    "invoice_date": "Date",
                    "quantity": "Units",
                }
            )
            st.dataframe(
                activity[["Product", "Invoice", "Date", "Units"]],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.markdown(
                '<div class="sw-empty">Imported transactions will show up here.</div>',
                unsafe_allow_html=True,
            )

if review_items:
    st.markdown('<div class="sw-section-heading">Replenishment priorities</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sw-section-caption">Products ordered by suggested replenishment quantity.</div>',
        unsafe_allow_html=True,
    )
    priority_left, priority_right = st.columns([1, 0.25], vertical_alignment="center")
    with priority_left:
        priority_frame = pd.DataFrame(review_items).rename(
            columns={
                "sku": "SKU",
                "name": "Product",
                "current_stock": "On hand",
                "reorder_point": "Reorder point",
                "recommended_order_qty": "Suggested order",
            }
        )
        st.dataframe(
            priority_frame[["SKU", "Product", "On hand", "Reorder point", "Suggested order"]].head(5),
            hide_index=True,
            use_container_width=True,
        )
    with priority_right:
        st.page_link(
            "pages/5_Reorder_Recommendations.py",
            label="View all recommendations",
            icon=":material/arrow_forward:",
            use_container_width=True,
        )

if data_end is not None:
    st.caption(
        f"Sales period: {current_period_start.strftime('%b %d, %Y')} – "
        f"{data_end.strftime('%b %d, %Y')} · Inventory last refreshed when this page loaded."
    )
