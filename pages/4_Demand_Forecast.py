import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import get_connection
from src.forecasting import compare_models, recursive_forecast
from src.preprocessing import select_eligible_products, aggregate_daily_demand, fill_missing_dates
from src.ui_components import page_title

page_title("Demand Forecast", "Train and compare models, then generate a 7-day demand forecast.")

with get_connection() as conn:
    rows = conn.execute(
        """
        SELECT p.sku, st.invoice_date, SUM(st.quantity) AS units_sold
        FROM sales_transactions st
        JOIN products p ON p.product_id = st.product_id
        GROUP BY p.sku, st.invoice_date
        ORDER BY st.invoice_date
        """
    ).fetchall()

if not rows:
    st.info("We need imported retail data before forecasting can run.")
    st.stop()

df = pd.DataFrame(rows)
df = df.rename(columns={"sku": "product_code", "invoice_date": "date", "units_sold": "units_sold"})
df["date"] = pd.to_datetime(df["date"])

daily = fill_missing_dates(aggregate_daily_demand(df.rename(columns={"date": "invoice_date", "product_code": "product_code"}).rename(columns={"invoice_date": "date"})))
eligible = select_eligible_products(daily, min_history_days=14, top_n=10)
if eligible.empty:
    st.warning("Not enough historical demand to support model training. Import more days or use a lower threshold.")
    st.stop()

selected = st.selectbox("Eligible product", eligible["product_code"].tolist())
model_choice = st.selectbox("Model", ["Linear Regression", "Random Forest", "Gradient Boosting", "Seasonal Naive"])

if st.button("Run forecast"):
    try:
        results, selected_model, _ = compare_models(daily, selected)
        st.subheader("Model comparison")
        metrics_df = pd.DataFrame(results)
        st.dataframe(metrics_df, use_container_width=True)

        forecast = recursive_forecast(daily, selected, model_name=model_choice, horizon=7)
        st.subheader("7-day forecast")
        st.dataframe(forecast, use_container_width=True)

        history = daily[daily["product_code"] == selected].sort_values("date").rename(columns={"units_sold": "actual"})
        forecast_plot = forecast.rename(columns={"forecast_date": "date", "predicted_quantity": "forecast"})
        chart_df = pd.DataFrame({
            "date": list(history["date"]) + list(pd.to_datetime(forecast_plot["date"])),
            "actual": list(history["actual"]) + [None] * len(forecast_plot),
            "forecast": [None] * len(history) + list(forecast_plot["forecast"]),
        })
        st.plotly_chart(
            px.line(chart_df, x="date", y=["actual", "forecast"], title=f"Demand history and forecast for {selected}"),
            use_container_width=True,
        )
    except ValueError as exc:
        st.error(str(exc))
