from __future__ import annotations

import pandas as pd

from src.forecasting import compare_models


def evaluate_model_set(daily_df: pd.DataFrame, product_code: str):
    results, selected_model, test_df = compare_models(daily_df, product_code)
    return {"results": results, "selected_model": selected_model, "test_df": test_df}
