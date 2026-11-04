from __future__ import annotations

import pandas as pd

from src.forecasting import compare_models, save_model_artifact


def train_product_model(daily_df: pd.DataFrame, product_code: str, model_name: str) -> dict:
    results, selected_model, _ = compare_models(daily_df, product_code)
    model_map = {
        "Linear Regression": "Linear Regression",
        "Random Forest": "Random Forest",
        "Gradient Boosting": "Gradient Boosting",
        "Seasonal Naive": "Seasonal Naive",
    }
    actual_model_name = model_map.get(model_name, model_name)
    if actual_model_name == "Seasonal Naive":
        metadata = {"model_name": actual_model_name, "product_code": product_code}
        save_model_artifact(actual_model_name, product_code, object(), metadata=metadata)
    return {"results": results, "selected_model": selected_model, "model_name": actual_model_name}
