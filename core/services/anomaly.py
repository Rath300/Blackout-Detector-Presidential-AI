import io

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


DEFAULT_CONTAMINATION = 0.02
MIN_DATA_ROWS = 25


def _normalize_columns(df):
    return {col: col.strip().lower() for col in df.columns}


def _map_columns(df):
    normalized = _normalize_columns(df)
    aliases = {
        "timestamp": [
            "date_time", "timestamp", "time", "datetime", "time_stamp", "ts", "date",
            "reading_time", "sample_time", "recorded_at",
        ],
        "ac_power": [
            "ac_power", "ac power", "acpower", "active_power", "real_power",
            "p_kw", "power_kw", "power_output", "output_power",
        ],
        "dc_power": [
            "dc_power", "dc power", "dcpower", "dc_input", "pdc",
        ],
        "energy": [
            "energy", "kwh", "wh", "mwh", "generation", "production", "output",
            "energy_kwh", "energy_mwh", "generated_kwh",
        ],
        "source": [
            "source_key", "source", "inverter", "device", "id", "unit", "device_id",
            "turbine_id", "unit_id", "meter_id", "generator_id", "asset_id", "well_id",
            "dam_id", "station_id", "plant_id", "transformer_id", "feeder_id",
        ],
        "efficiency": [
            "efficiency", "eff", "conversion", "yield", "performance",
            "capacity_factor", "cf", "heat_rate",
        ],
        "value": [
            "value", "reading", "measurement", "output_mw", "output_kw",
            "generation_mw", "active_power",
        ],
        # Wind-specific
        "wind_speed":  ["wind_speed", "wind speed", "ws", "wind_velocity", "anemometer"],
        "rotor_speed": ["rotor_speed", "rpm", "rotor speed", "rotation_speed", "shaft_speed"],
        # Hydro-specific
        "flow_rate":   ["flow_rate", "flow rate", "water_flow", "discharge", "q_m3s", "streamflow"],
        "head":        ["head", "hydraulic_head", "net_head", "gross_head"],
        # Fossil / gas-specific
        "fuel_flow":   ["fuel_flow", "fuel_consumption", "gas_flow", "fuel_rate"],
        "load_factor": ["load_factor", "load_pct", "load percent", "utilization"],
        # Grid / substation
        "voltage":     ["voltage", "v_kv", "voltage_kv", "bus_voltage", "grid_voltage"],
        "frequency":   ["frequency", "freq_hz", "grid_freq", "hz"],
        "current":     ["current", "amps", "current_a", "line_current"],
        "thd":         ["thd", "total_harmonic_distortion", "harmonic"],
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

    # Priority order for the primary value column – covers all source types
    value_candidates = [
        col_map.get("ac_power"),
        col_map.get("dc_power"),
        col_map.get("energy"),
        col_map.get("value"),
        col_map.get("wind_speed"),
        col_map.get("flow_rate"),
        col_map.get("fuel_flow"),
        col_map.get("voltage"),
        col_map.get("rotor_speed"),
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

    # Carry through any extra signal columns that are present
    for extra_key in ("wind_speed", "rotor_speed", "flow_rate", "fuel_flow", "voltage", "frequency", "current"):
        col = col_map.get(extra_key)
        if col and col in df.columns:
            df[extra_key.upper()] = pd.to_numeric(df[col], errors="coerce")

    return df


def detect_anomalies(df, contamination=DEFAULT_CONTAMINATION):
    df = df.copy()
    if len(df) < MIN_DATA_ROWS:
        df["anomaly"] = False
        df["anomaly_score"] = 0.0
        return df

    features = df[["Value"]].copy()

    # Time features
    if "TIME_STAMP" in df.columns:
        ts = pd.to_datetime(df["TIME_STAMP"])
        features["hour_normalized"] = ts.dt.hour / 24
        features["day_normalized"] = ts.dt.dayofweek / 7

    # Rate-of-change feature (helps detect sudden spikes / drops across all source types)
    features["delta"] = df["Value"].diff().fillna(0)
    features["rolling_mean"] = df["Value"].rolling(5, min_periods=1).mean()
    features["rolling_std"]  = df["Value"].rolling(5, min_periods=1).std().fillna(0)

    # Extra signal columns if present (e.g. WIND_SPEED, VOLTAGE)
    for extra in ("WIND_SPEED", "ROTOR_SPEED", "FLOW_RATE", "FUEL_FLOW", "VOLTAGE", "FREQUENCY"):
        if extra in df.columns:
            features[extra.lower()] = pd.to_numeric(df[extra], errors="coerce").fillna(0)

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
    df["rolling_std_3"]  = df["AC_POWER_FIXED"].rolling(window=3, min_periods=1).std().fillna(0)
    df["rolling_mean_7"] = df["AC_POWER_FIXED"].rolling(window=7, min_periods=1).mean()
    df["lag_1"] = df["AC_POWER_FIXED"].shift(1).fillna(df["AC_POWER_FIXED"].mean())
    df["lag_2"] = df["AC_POWER_FIXED"].shift(2).fillna(df["AC_POWER_FIXED"].mean())

    feature_cols = [
        "time_index", "hour", "day_of_week", "month", "day_of_year",
        "is_weekend", "rolling_mean_3", "rolling_std_3", "rolling_mean_7", "lag_1", "lag_2",
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
    metrics = {"train_rows": int(len(X_train)), "test_rows": int(len(X_test))}
    return df_forecast, metrics, ""
