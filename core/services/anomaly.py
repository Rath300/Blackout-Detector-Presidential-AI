import io

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


DEFAULT_CONTAMINATION = 0.02
MIN_DATA_ROWS = 25


def _normalize_columns(df):
    normalized = {col: col.strip().lower() for col in df.columns}
    return normalized


def _map_columns(df):
    normalized = _normalize_columns(df)
    aliases = {
        "timestamp": ["date_time", "timestamp", "time", "datetime", "time_stamp"],
        "ac_power": ["ac_power", "ac power", "acpower"],
        "dc_power": ["dc_power", "dc power", "dcpower"],
        "energy": ["energy", "kwh", "wh", "generation", "production"],
        "source": ["source_key", "source", "inverter", "device", "id", "unit", "device_id"],
        "efficiency": ["efficiency", "eff", "conversion", "yield", "performance"],
        "value": ["value"],
    }
    mapped = {}
    for key, choices in aliases.items():
        for choice in choices:
            for col, norm in normalized.items():
                if choice == norm:
                    mapped[key] = col
                    break
            if key in mapped:
                break
    return mapped


def load_inverter_csv(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    return preprocess_inverter_data(df)


def load_inverter_json(payload):
    df = pd.DataFrame(payload)
    return preprocess_inverter_data(df)


def preprocess_inverter_data(df):
    if df is None or df.empty:
        return pd.DataFrame()

    col_map = _map_columns(df)
    timestamp_col = col_map.get("timestamp")
    if not timestamp_col and "TIME_STAMP" in df.columns:
        timestamp_col = "TIME_STAMP"
    if not timestamp_col:
        return pd.DataFrame()

    df = df.copy()
    df["TIME_STAMP"] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df.dropna(subset=["TIME_STAMP"])

    value_candidates = [
        col_map.get("ac_power"),
        col_map.get("dc_power"),
        col_map.get("energy"),
        col_map.get("value"),
    ]
    value_col = next((c for c in value_candidates if c and c in df.columns), None)

    if not value_col:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        value_col = numeric_cols[0] if numeric_cols else None

    if not value_col:
        return pd.DataFrame()

    df["Value"] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["Value"])
    df = df.sort_values("TIME_STAMP").reset_index(drop=True)
    df["time_index"] = range(len(df))

    if col_map.get("ac_power") and col_map.get("dc_power"):
        df["AC_POWER_FIXED"] = pd.to_numeric(df[col_map["ac_power"]], errors="coerce").fillna(0)
        df["DC_POWER_INPUT"] = pd.to_numeric(df[col_map["dc_power"]], errors="coerce").replace(0, np.nan)
        df["EFFICIENCY_%"] = (df["AC_POWER_FIXED"] / df["DC_POWER_INPUT"]) * 100
        df["EFFICIENCY_%"] = df["EFFICIENCY_%"].clip(0, 100)
    elif col_map.get("efficiency"):
        df["EFFICIENCY_%"] = pd.to_numeric(df[col_map["efficiency"]], errors="coerce")
        df["AC_POWER_FIXED"] = df["Value"]
    else:
        df["EFFICIENCY_%"] = np.nan
        df["AC_POWER_FIXED"] = df["Value"]

    if col_map.get("source"):
        df["SOURCE_ID"] = df[col_map["source"]].astype(str)
        df["SOURCE_ID_NUMBER"] = pd.factorize(df["SOURCE_ID"])[0] + 1
    else:
        df["SOURCE_ID"] = "Main System"
        df["SOURCE_ID_NUMBER"] = 1

    return df


def detect_anomalies(df, contamination=DEFAULT_CONTAMINATION):
    df = df.copy()
    if len(df) < MIN_DATA_ROWS:
        df["anomaly"] = False
        df["anomaly_score"] = 0.0
        return df

    features = df[["Value"]].copy()
    if "TIME_STAMP" in df.columns:
        df["hour"] = pd.to_datetime(df["TIME_STAMP"]).dt.hour
        df["day_of_week"] = pd.to_datetime(df["TIME_STAMP"]).dt.dayofweek
        features["hour_normalized"] = df["hour"] / 24
        features["day_normalized"] = df["day_of_week"] / 7

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=200,
        max_samples="auto",
        max_features=1.0,
    )
    df["anomaly"] = model.fit_predict(features_scaled) == -1
    df["anomaly_score"] = model.score_samples(features_scaled)
    return df


def run_forecast(df, model_type="gradient_boosting"):
    df = df.copy()
    df["TIME_STAMP"] = pd.to_datetime(df["TIME_STAMP"], errors="coerce")
    df = df.dropna(subset=["TIME_STAMP", "AC_POWER_FIXED"])

    if len(df) < 50:
        return pd.DataFrame(), {}, "Need at least 50 data points for forecasting"

    df["time_index"] = range(len(df))
    df["hour"] = df["TIME_STAMP"].dt.hour
    df["day_of_week"] = df["TIME_STAMP"].dt.dayofweek
    df["month"] = df["TIME_STAMP"].dt.month
    df["day_of_year"] = df["TIME_STAMP"].dt.dayofyear
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    df["rolling_mean_3"] = df["AC_POWER_FIXED"].rolling(window=3, min_periods=1).mean()
    df["rolling_std_3"] = df["AC_POWER_FIXED"].rolling(window=3, min_periods=1).std().fillna(0)
    df["rolling_mean_7"] = df["AC_POWER_FIXED"].rolling(window=7, min_periods=1).mean()

    df["lag_1"] = df["AC_POWER_FIXED"].shift(1).fillna(df["AC_POWER_FIXED"].mean())
    df["lag_2"] = df["AC_POWER_FIXED"].shift(2).fillna(df["AC_POWER_FIXED"].mean())

    feature_cols = [
        "time_index",
        "hour",
        "day_of_week",
        "month",
        "day_of_year",
        "is_weekend",
        "rolling_mean_3",
        "rolling_std_3",
        "rolling_mean_7",
        "lag_1",
        "lag_2",
    ]

    X = df[feature_cols].fillna(0)
    y = df["AC_POWER_FIXED"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )

    if model_type == "linear_regression":
        from sklearn.linear_model import LinearRegression

        model = LinearRegression()
    elif model_type == "random_forest":
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(n_estimators=200, random_state=42)
    else:
        from sklearn.ensemble import GradientBoostingRegressor

        model = GradientBoostingRegressor(random_state=42)

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    df_forecast = df.iloc[-len(predictions):].copy()
    df_forecast["prediction"] = predictions
    metrics = {
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
    }
    return df_forecast, metrics, ""
