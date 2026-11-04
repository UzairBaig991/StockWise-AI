import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import fetch_model_runs, get_connection
from src.forecasting import compare_models, list_saved_model_metadata
from src.preprocessing import aggregate_daily_demand, fill_missing_dates
from src.ui_components import metric_card, page_title

page_title(
    "Model Performance",
    "Inspect chronological holdout results, prediction errors, and saved model metadata.",
)

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
    st.info("Import sales data first to evaluate forecasting models.")
    st.stop()

sales = pd.DataFrame(rows).rename(
    columns={"sku": "product_code", "invoice_date": "date"}
)
sales["date"] = pd.to_datetime(sales["date"])
daily = fill_missing_dates(aggregate_daily_demand(sales))
products = sorted(daily["product_code"].unique().tolist())
selected_product = st.selectbox("Product", products)

if st.button("Run chronological evaluation", type="primary"):
    try:
        model_results, best_model, predictions = compare_models(daily, selected_product)
        st.session_state["model_diagnostics"] = {
            "product_code": selected_product,
            "results": model_results,
            "best_model": best_model,
            "predictions": predictions,
        }
    except ValueError as exc:
        st.error(str(exc))

diagnostics = st.session_state.get("model_diagnostics")
if diagnostics and diagnostics["product_code"] == selected_product:
    predictions = diagnostics["predictions"]
    result_table = pd.DataFrame(diagnostics["results"])
    successful = result_table[result_table["mae"].notna()].sort_values("mae")
    best_model = diagnostics["best_model"]

    st.subheader("Evaluation overview")
    if not successful.empty:
        best_row = successful.iloc[0]
        baseline_rows = successful[successful["model_name"] == "Seasonal Naive"]
        baseline_mae = float(baseline_rows["mae"].iloc[0]) if not baseline_rows.empty else None
        improvement = (
            (baseline_mae - float(best_row["mae"])) / baseline_mae * 100
            if baseline_mae is not None and baseline_mae > 0
            else None
        )
        columns = st.columns(4)
        with columns[0]:
            metric_card("Selected model", str(best_model), "lowest holdout MAE")
        with columns[1]:
            metric_card("MAE", f"{float(best_row['mae']):.2f}", "units per day")
        with columns[2]:
            metric_card("RMSE", f"{float(best_row['rmse']):.2f}", "units per day")
        with columns[3]:
            delta = f"{improvement:+.1f}% vs baseline" if improvement is not None else "baseline comparison"
            metric_card("MAE change", f"{improvement:+.1f}%" if improvement is not None else "N/A", delta)

    st.caption(
        f"Evaluation period: {predictions['date'].min().date()} to {predictions['date'].max().date()} "
        f"({len(predictions)} holdout days). Chronological split; each test prediction uses earlier observations only. "
        "Lower MAE and RMSE are better; they are not accuracy percentages."
    )
    st.subheader("Model comparison")
    st.dataframe(result_table, use_container_width=True, hide_index=True)
    failures = result_table[result_table["error"].notna()] if "error" in result_table else pd.DataFrame()
    if not failures.empty:
        with st.expander("Models that could not be evaluated"):
            st.dataframe(failures[["model_name", "error"]], use_container_width=True, hide_index=True)

    plot_data = predictions[["date", "actual", best_model]].rename(
        columns={best_model: "predicted"}
    )
    long_data = plot_data.melt(
        id_vars="date", var_name="series", value_name="units"
    )
    st.subheader(f"Actual vs predicted — {best_model}")
    st.plotly_chart(
        px.line(
            long_data,
            x="date",
            y="units",
            color="series",
            markers=True,
            labels={"date": "Date", "units": "Units sold", "series": ""},
        ),
        use_container_width=True,
    )

    residual_data = predictions[["date", "actual", best_model]].copy()
    residual_data["predicted"] = residual_data[best_model]
    residual_data["residual"] = residual_data["actual"] - residual_data["predicted"]
    residual_columns = st.columns(2)
    with residual_columns[0]:
        st.subheader("Residuals over time")
        st.plotly_chart(
            px.scatter(
                residual_data,
                x="date",
                y="residual",
                labels={"date": "Date", "residual": "Actual - predicted (units)"},
                title="Positive residuals mean under-forecasting",
            ).add_hline(y=0, line_dash="dash", line_color="#64748b"),
            use_container_width=True,
        )
    with residual_columns[1]:
        st.subheader("Prediction error distribution")
        st.plotly_chart(
            px.histogram(
                residual_data,
                x="residual",
                nbins=20,
                labels={"residual": "Actual - predicted (units)"},
                title="Residual frequency",
            ),
            use_container_width=True,
        )

    st.subheader("Largest holdout errors")
    largest_errors = residual_data.assign(
        absolute_error=lambda frame: frame["residual"].abs()
    ).sort_values("absolute_error", ascending=False)
    st.dataframe(
        largest_errors[["date", "actual", "predicted", "residual", "absolute_error"]]
        .head(10)
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Run an evaluation to see prediction diagnostics for this product.")

st.subheader("Saved evaluation history")
model_runs = fetch_model_runs(limit=10)
if model_runs:
    run_table = pd.DataFrame(model_runs)
    st.dataframe(
        run_table[
            [
                "model_name",
                "train_end_date",
                "test_start_date",
                "mae",
                "rmse",
                "baseline_mae",
                "created_at",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    latest_run = run_table.iloc[0]
    with st.expander("Latest evaluation metadata"):
        st.json(latest_run["metadata_json"])
else:
    st.info("No evaluation runs have been saved yet.")

saved_artifacts = list_saved_model_metadata()
if saved_artifacts:
    st.subheader("Saved model artifacts")
    artifact_frame = pd.DataFrame(saved_artifacts)
    st.dataframe(
        artifact_frame[["artifact_name", "model_name", "product_code"]],
        use_container_width=True,
        hide_index=True,
    )
    chosen_artifact = st.selectbox(
        "Artifact details", artifact_frame["artifact_name"].tolist()
    )
    metadata = artifact_frame.loc[
        artifact_frame["artifact_name"] == chosen_artifact, "metadata"
    ].iloc[0]
    st.json(metadata)
