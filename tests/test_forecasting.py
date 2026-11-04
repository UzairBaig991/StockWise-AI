import pandas as pd

from src.forecasting import compare_models, recursive_forecast


def test_recursive_forecast_returns_horizon_values_non_negative():
    df = pd.DataFrame(
        {
            "product_code": ["P1"] * 30,
            "date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "units_sold": [10, 12, 9, 11, 13, 15, 12, 10, 16, 14, 12, 15, 17, 13, 11, 18, 16, 14, 19, 20, 17, 15, 16, 18, 19, 17, 21, 22, 20, 18],
        }
    )

    forecast = recursive_forecast(df, "P1", model_name="Linear Regression", horizon=7)
    assert len(forecast) == 7
    assert (forecast["predicted_quantity"] >= 0).all()


def test_model_comparison_returns_real_holdout_predictions(monkeypatch):
    daily = pd.DataFrame(
        {
            "product_code": ["P2"] * 90,
            "date": pd.date_range("2024-01-01", periods=90, freq="D"),
            "units_sold": [float((day % 7) * 3 + day // 10) for day in range(90)],
        }
    )
    monkeypatch.setattr("src.forecasting.save_model_run", lambda **kwargs: None)

    results, selected_model, diagnostics = compare_models(daily, "P2")

    assert selected_model in {"Seasonal Naive", "Linear Regression", "Random Forest", "Gradient Boosting"}
    assert {"actual", "Seasonal Naive", "Linear Regression", "residual"} <= set(diagnostics.columns)
    assert len(diagnostics) > 0
    assert (diagnostics["actual"] != diagnostics["Linear Regression"]).any()
    assert (diagnostics["residual"] == diagnostics["actual"] - diagnostics[selected_model]).all()
    assert all("mae" in result for result in results)
