from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.config import MODELS_DIR
from src.database import save_model_run
from src.feature_engineering import create_leakage_safe_features, split_time_series


FEATURE_COLUMNS = ["lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_28", "day_of_week", "month", "is_weekend"]


def _prepare_product_history(daily_df: pd.DataFrame, product_code: str) -> pd.DataFrame:
    product_df = daily_df[daily_df["product_code"] == product_code].copy()
    product_df = product_df.sort_values("date").reset_index(drop=True)
    if product_df.empty:
        raise ValueError(f"No historical data found for product {product_code}.")
    product_df["date"] = pd.to_datetime(product_df["date"]).dt.normalize()
    product_df = product_df.loc[product_df.groupby("date")["units_sold"].transform("sum").notna()]
    return product_df


def _build_modeling_frame(daily_df: pd.DataFrame, product_code: str) -> pd.DataFrame:
    history = _prepare_product_history(daily_df, product_code)
    feature_df = create_leakage_safe_features(history)
    feature_df = feature_df[feature_df["lag_1"].notna() & feature_df["lag_7"].notna() & feature_df["lag_14"].notna()].copy()
    feature_df["target"] = feature_df["units_sold"]
    return feature_df


def _safe_rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _seasonal_naive_predict(train_df: pd.DataFrame, test_df: pd.DataFrame) -> np.ndarray:
    del train_df
    return test_df["lag_7"].fillna(0).to_numpy(dtype=float)


def compare_models(daily_df: pd.DataFrame, product_code: str) -> tuple[list[dict[str, float | str]], str, pd.DataFrame]:
    modeling_df = _build_modeling_frame(daily_df, product_code)
    if modeling_df.empty:
        raise ValueError(f"Not enough data to compare models for product {product_code}.")

    train_df, test_df = split_time_series(modeling_df, test_fraction=0.2)
    if train_df.empty or test_df.empty:
        raise ValueError(f"Product {product_code} does not have enough time periods for a valid train/test split.")

    y_true = test_df["units_sold"].to_numpy(dtype=float)
    results: list[dict[str, float | str]] = []
    prediction_frame = test_df[["date", "units_sold"]].rename(columns={"units_sold": "actual"}).copy()

    baseline_pred = _seasonal_naive_predict(train_df, test_df)
    prediction_frame["Seasonal Naive"] = baseline_pred
    results.append(
        {
            "model_name": "Seasonal Naive",
            "mae": float(mean_absolute_error(y_true, baseline_pred)),
            "rmse": _safe_rmse(y_true, baseline_pred),
            "baseline_mae": float(mean_absolute_error(y_true, baseline_pred)),
        }
    )

    pipeline_map = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(random_state=42),
    }

    for name, model in pipeline_map.items():
        try:
            X_train = train_df[FEATURE_COLUMNS].fillna(0)
            y_train = train_df["units_sold"].fillna(0)
            X_test = test_df[FEATURE_COLUMNS].fillna(0)
            model.fit(X_train, y_train)
            predictions = np.clip(model.predict(X_test), 0, None)
            prediction_frame[name] = predictions
            results.append(
                {
                    "model_name": name,
                    "mae": float(mean_absolute_error(y_true, predictions)),
                    "rmse": _safe_rmse(y_true, predictions),
                    "baseline_mae": float(results[0]["mae"]),
                }
            )
        except (ValueError, TypeError, FloatingPointError) as exc:
            results.append({"model_name": name, "error": str(exc)})

    successful_results = [result for result in results if "mae" in result]
    if not successful_results:
        raise ValueError("No candidate model produced valid evaluation metrics.")
    selected = min(successful_results, key=lambda item: float(item["mae"]))
    selected_name = str(selected["model_name"])
    prediction_frame["residual"] = prediction_frame["actual"] - prediction_frame[selected_name]
    save_model_run(
        model_name=selected_name,
        train_end_date=str(train_df["date"].max().date()) if not train_df.empty else None,
        test_start_date=str(test_df["date"].min().date()) if not test_df.empty else None,
        mae=float(selected["mae"]),
        rmse=float(selected["rmse"]),
        baseline_mae=float(results[0]["mae"]),
        metadata_json={
            "product_code": product_code,
            "selected_model": selected_name,
            "test_rows": int(len(test_df)),
            "model_results": results,
            "feature_columns": FEATURE_COLUMNS,
            "evaluation_method": "chronological holdout; one-step predictions with earlier actual observations",
            "failed_models": [result for result in results if "error" in result],
        },
    )
    return results, selected_name, prediction_frame


def _feature_row_for_date(history_df: pd.DataFrame, future_date: pd.Timestamp) -> dict[str, float | int]:
    lag_1 = float(history_df[history_df["date"] == future_date - pd.Timedelta(days=1)]["units_sold"].sum()) if not history_df[history_df["date"] == future_date - pd.Timedelta(days=1)].empty else 0.0
    lag_7 = float(history_df[history_df["date"] == future_date - pd.Timedelta(days=7)]["units_sold"].sum()) if not history_df[history_df["date"] == future_date - pd.Timedelta(days=7)].empty else 0.0
    lag_14 = float(history_df[history_df["date"] == future_date - pd.Timedelta(days=14)]["units_sold"].sum()) if not history_df[history_df["date"] == future_date - pd.Timedelta(days=14)].empty else 0.0
    past_7_window = history_df[(history_df["date"] < future_date) & (history_df["date"] >= future_date - pd.Timedelta(days=7))]["units_sold"].tolist()
    past_28_window = history_df[(history_df["date"] < future_date) & (history_df["date"] >= future_date - pd.Timedelta(days=28))]["units_sold"].tolist()
    row = {
        "lag_1": lag_1,
        "lag_7": lag_7,
        "lag_14": lag_14,
        "rolling_mean_7": float(np.mean(past_7_window)) if past_7_window else 0.0,
        "rolling_mean_28": float(np.mean(past_28_window)) if past_28_window else 0.0,
        "day_of_week": future_date.day_of_week,
        "month": future_date.month,
        "is_weekend": 1 if future_date.day_of_week >= 5 else 0,
    }
    return row


def recursive_forecast(daily_df: pd.DataFrame, product_code: str, model_name: str = "Linear Regression", horizon: int = 7) -> pd.DataFrame:
    history = _prepare_product_history(daily_df, product_code).copy()
    if history.empty:
        raise ValueError(f"No data available for product {product_code}.")

    trend = history.sort_values("date").copy()
    trend = create_leakage_safe_features(trend)
    model = None
    model_path = MODELS_DIR / f"{product_code.replace('/', '_')}_{model_name.replace(' ', '_')}.joblib"
    if model_path.exists():
        model = joblib.load(model_path)

    if model is None:
        train_df, _ = split_time_series(trend, test_fraction=0.2)
        if train_df.empty:
            raise ValueError(f"No trainable history available for {product_code}.")
        X_train = train_df[FEATURE_COLUMNS].fillna(0)
        y_train = train_df["units_sold"].fillna(0)
        if model_name == "Seasonal Naive":
            model = "Seasonal Naive"
        elif model_name == "Linear Regression":
            model = LinearRegression()
            model.fit(X_train, y_train)
        elif model_name == "Random Forest":
            model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train)
        elif model_name == "Gradient Boosting":
            model = GradientBoostingRegressor(random_state=42)
            model.fit(X_train, y_train)
        else:
            raise ValueError(f"Unsupported model: {model_name}")

    future_rows = []
    last_date = trend["date"].max().to_pydatetime()
    for step in range(1, horizon + 1):
        future_date = pd.Timestamp(last_date) + pd.Timedelta(days=step)
        feature_row = _feature_row_for_date(trend, future_date)
        if model_name == "Seasonal Naive":
            pred = float(trend[trend["date"] == (future_date - pd.Timedelta(days=7))]["units_sold"].sum()) if not trend[trend["date"] == (future_date - pd.Timedelta(days=7))].empty else 0.0
        else:
            X = pd.DataFrame([feature_row], columns=FEATURE_COLUMNS)
            pred = float(model.predict(X)[0])
        pred = max(0.0, float(pred))
        future_rows.append({"forecast_date": future_date.strftime("%Y-%m-%d"), "predicted_quantity": round(pred, 2), "model_name": model_name})
        trend = pd.concat([
            trend,
            pd.DataFrame([{"product_code": product_code, "date": future_date, "units_sold": pred}])
        ], ignore_index=True)
    return pd.DataFrame(future_rows)


def save_model_artifact(model_name: str, product_code: str, model_object, metadata: dict | None = None) -> str:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{product_code.replace('/', '_')}_{model_name.replace(' ', '_')}.joblib"
    path = MODELS_DIR / file_name
    payload = {"model": model_object, "metadata": metadata or {}}
    joblib.dump(payload, path)
    return str(path)


def load_saved_model(product_code: str, model_name: str):
    model_path = MODELS_DIR / f"{product_code.replace('/', '_')}_{model_name.replace(' ', '_')}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"No saved model found at {model_path}.")
    payload = joblib.load(model_path)
    return payload.get("model"), payload.get("metadata", {})


def list_saved_model_metadata() -> list[dict[str, object]]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for artifact_path in sorted(MODELS_DIR.glob("*.joblib")):
        try:
            payload = joblib.load(artifact_path)
        except Exception:
            continue
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        rows.append(
            {
                "artifact_name": artifact_path.name,
                "model_name": metadata.get("model_name", artifact_path.stem),
                "product_code": metadata.get("product_code", artifact_path.stem.split("_")[0]),
                "metadata": metadata,
            }
        )
    return rows
