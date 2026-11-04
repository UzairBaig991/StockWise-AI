import pandas as pd

from src.feature_engineering import create_leakage_safe_features


def test_create_leakage_safe_features_has_safe_lags():
    df = pd.DataFrame(
        {
            "product_code": ["P1", "P1", "P1", "P1", "P1", "P1", "P1", "P1"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06", "2024-01-07", "2024-01-08"]),
            "units_sold": [10, 12, 15, 8, 20, 18, 22, 25],
        }
    )

    features = create_leakage_safe_features(df)
    assert features["lag_1"].iloc[0] is None or pd.isna(features["lag_1"].iloc[0])
    assert features["lag_7"].iloc[7] == 10
    assert features["rolling_mean_7"].iloc[7] > 0
