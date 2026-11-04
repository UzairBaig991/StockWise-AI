from __future__ import annotations

import pandas as pd


def create_leakage_safe_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df.empty:
        return daily_df.copy()

    features = daily_df.copy()
    features["date"] = pd.to_datetime(features["date"]).dt.normalize()
    features = features.sort_values(["product_code", "date"]).copy()
    features["lag_1"] = features.groupby("product_code")["units_sold"].shift(1)
    features["lag_7"] = features.groupby("product_code")["units_sold"].shift(7)
    features["lag_14"] = features.groupby("product_code")["units_sold"].shift(14)
    features["rolling_mean_7"] = (
        features.groupby("product_code")["units_sold"].transform(lambda s: s.shift(1).rolling(window=7, min_periods=1).mean())
    )
    features["rolling_mean_28"] = (
        features.groupby("product_code")["units_sold"].transform(lambda s: s.shift(1).rolling(window=28, min_periods=1).mean())
    )
    features["day_of_week"] = features["date"].dt.day_of_week
    features["month"] = features["date"].dt.month
    features["is_weekend"] = features["date"].dt.day_of_week.isin([5, 6]).astype(int)
    features["product_code"] = features["product_code"].astype(str)
    return features


def split_time_series(df: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()

    sorted_df = df.sort_values(["product_code", "date"]).copy()
    last_dates = sorted_df.groupby("product_code")["date"].max().reset_index()
    cutoff_map = {}
    for _, row in last_dates.iterrows():
        unique_dates = sorted_df[sorted_df["product_code"] == row["product_code"]]["date"].drop_duplicates().sort_values()
        if len(unique_dates) < 2:
            cutoff_map[row["product_code"]] = unique_dates.iloc[0]
        else:
            split_index = max(1, int(len(unique_dates) * (1 - test_fraction)))
            cutoff_map[row["product_code"]] = unique_dates.iloc[split_index - 1]

    train_frames = []
    test_frames = []
    for product_code, group in sorted_df.groupby("product_code"):
        cutoff = cutoff_map.get(product_code)
        if cutoff is None:
            train_frames.append(group)
            continue
        train = group[group["date"] <= cutoff].copy()
        test = group[group["date"] > cutoff].copy()
        if not train.empty:
            train_frames.append(train)
        if not test.empty:
            test_frames.append(test)

    return pd.concat(train_frames, ignore_index=True), pd.concat(test_frames, ignore_index=True)


def add_model_target(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["target"] = result["units_sold"]
    return result
