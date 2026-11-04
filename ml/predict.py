from __future__ import annotations

import pandas as pd

from src.forecasting import recursive_forecast


def forecast_product(daily_df: pd.DataFrame, product_code: str, model_name: str = "Linear Regression", horizon: int = 7) -> pd.DataFrame:
    return recursive_forecast(daily_df, product_code, model_name=model_name, horizon=horizon)
