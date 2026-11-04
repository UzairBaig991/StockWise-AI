# Methodology

The project aggregates positive transaction quantities into daily product demand. Feature engineering uses only information available up to the current date and avoids leakage from future values. Models are compared with a chronological split, and the forecast is generated recursively over seven days.

The Model Performance page shows holdout predictions and residual diagnostics (actual minus predicted). A positive residual indicates under-forecasting. MAE and RMSE are measured in units and are not accuracy percentages. Model evaluation history is saved to SQLite.

The Sales Analytics page can export a ZIP containing the current filtered sales data and summaries, the full inventory/reorder snapshot, recent model evaluation history, and a manifest describing each CSV.
