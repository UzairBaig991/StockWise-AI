from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import fetch_inventory_rows, fetch_products, get_connection
from src.inventory_logic import compute_reorder_metrics
from src.ui_components import metric_card, page_title

page_title("Dashboard", "Real-time inventory intelligence for your business.")

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
    window_start = data_end - pd.Timedelta(days=29)
    recent_sales = sales[sales["invoice_date"] >= window_start]
    product_daily_demand = sales.groupby("sku")["units_sold"].mean().to_dict()
else:
    data_end = None
    recent_sales = sales
    product_daily_demand = {}

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
                    "recommended_order_qty": metrics["recommended_order_qty"],
                }
            )

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
    health_caption = (
        f"{len(inventory_rows) - len(review_items)} of {len(inventory_rows)} stocked products are above their reorder point."
        if health_score is not None
        else "Import sales and configure stock to calculate inventory health."
    )
    st.markdown(
        f"""
        <div class="sw-panel">
            <div class="sw-panel-title">Stock health</div>
            <div class="sw-panel-caption">Reorder risk across tracked inventory</div>
            <div class="sw-health">
                <div class="sw-health-ring" style="--health-score:{score}%">
                    <div class="sw-health-ring-inner">
                        <div class="sw-health-score">{score_label}</div>
                        <div class="sw-health-percent">HEALTHY</div>
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
        metric_card("Units sold", f"{recent_sales['units_sold'].sum():,.0f}", "latest 30 data days")
    metric_bottom = st.columns(2, gap="small")
    with metric_bottom[0]:
        metric_card("Units on hand", f"{on_hand_units:,.0f}", "configured inventory")
    with metric_bottom[1]:
        metric_card(
            "Reorder alerts",
            f"{len(review_items):,}" if not sales.empty else "—",
            "products at or below reorder point" if not sales.empty else "import sales to calculate",
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
elif not sales.empty:
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
else:
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

st.write("")
chart_panel, activity_panel = st.columns([1.25, 0.75], gap="medium")
with chart_panel:
    with st.container(border=True):
        st.markdown(
            '<div class="sw-panel-title">Daily demand</div>'
            '<div class="sw-panel-caption">Units sold across the latest 30 data days</div>',
            unsafe_allow_html=True,
        )
        if not recent_sales.empty:
            trend = (
                recent_sales.groupby("invoice_date", as_index=False)["units_sold"]
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
                height=250,
            )
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.markdown(
                '<div class="sw-empty">Your sales trend will appear here after you import data.</div>',
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

if data_end is not None:
    st.caption(f"Showing activity through {data_end.strftime('%b %d, %Y')}.")
