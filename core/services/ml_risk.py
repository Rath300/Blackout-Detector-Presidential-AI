import glob
import os
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.calibration import calibration_curve


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
MODEL_PATH = os.path.join(DATA_DIR, "risk_model.pkl")
COUNTY_RISK_PATH = os.path.join(DATA_DIR, "county_risk.csv")
METRICS_PATH = os.path.join(DATA_DIR, "risk_model_metrics.json")
STORM_GLOB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "StormEvents_details-*.csv.gz")
SVI_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "svi_interactive_map.csv")


OUTAGE_EVENT_TYPES = {
    "Thunderstorm Wind",
    "High Wind",
    "Hurricane",
    "Tornado",
    "Ice Storm",
    "Winter Storm",
    "Heavy Snow",
    "Blizzard",
    "Tropical Storm",
    "Flood",
    "Flash Flood",
    "Coastal Flood",
}


def _parse_damage(value):
    if pd.isna(value):
        return 0.0
    value = str(value).strip()
    if not value:
        return 0.0
    multiplier = 1.0
    if value[-1].upper() == "K":
        multiplier = 1_000.0
        value = value[:-1]
    elif value[-1].upper() == "M":
        multiplier = 1_000_000.0
        value = value[:-1]
    elif value[-1].upper() == "B":
        multiplier = 1_000_000_000.0
        value = value[:-1]
    try:
        return float(value) * multiplier
    except ValueError:
        return 0.0


def _load_storm_events():
    files = sorted(glob.glob(STORM_GLOB))
    if not files:
        return pd.DataFrame()

    frames = []
    for path in files:
        frames.append(pd.read_csv(path))
    df = pd.concat(frames, ignore_index=True)
    return df


def _load_svi():
    if not os.path.exists(SVI_PATH):
        return pd.DataFrame()
    df = pd.read_csv(SVI_PATH, dtype={"FIPS": str})
    df["FIPS"] = df["FIPS"].str.zfill(5)
    return df


def _prepare_training_data(df):
    df = df.copy()
    df["STATE_FIPS_STR"] = df["STATE_FIPS"].astype(str).str.zfill(2)
    df["COUNTY_FIPS_STR"] = df["CZ_FIPS"].astype(str).str.zfill(3)
    df["FIPS"] = df["STATE_FIPS_STR"] + df["COUNTY_FIPS_STR"]

    svi = _load_svi()
    if not svi.empty:
        svi = svi[["FIPS", "RPL_THEMES"]].rename(columns={"RPL_THEMES": "SVI_SCORE"})
        df = df.merge(svi, on="FIPS", how="left")
    else:
        df["SVI_SCORE"] = 0

    df["DAMAGE_PROPERTY_NUM"] = df["DAMAGE_PROPERTY"].apply(_parse_damage)
    df["DAMAGE_CROPS_NUM"] = df["DAMAGE_CROPS"].apply(_parse_damage)
    df["INJURIES"] = df["INJURIES_DIRECT"].fillna(0) + df["INJURIES_INDIRECT"].fillna(0)
    df["DEATHS"] = df["DEATHS_DIRECT"].fillna(0) + df["DEATHS_INDIRECT"].fillna(0)

    df["IS_OUTAGE_EVENT"] = df["EVENT_TYPE"].isin(OUTAGE_EVENT_TYPES).astype(int)
    df["POWER_OUTAGE_LIKELY"] = (
        (df["IS_OUTAGE_EVENT"] == 1)
        & (
            (df["DAMAGE_PROPERTY_NUM"] >= 1_000_000)
            | (df["INJURIES"] > 0)
            | (df["DEATHS"] > 0)
        )
    ).astype(int)

    features = df[
        [
            "DAMAGE_PROPERTY_NUM",
            "DAMAGE_CROPS_NUM",
            "INJURIES",
            "DEATHS",
            "MAGNITUDE",
            "BEGIN_LAT",
            "BEGIN_LON",
            "SVI_SCORE",
        ]
    ].fillna(0)

    event_type_dummies = pd.get_dummies(df["EVENT_TYPE"], prefix="event")
    X = pd.concat([features, event_type_dummies], axis=1)
    y = df["POWER_OUTAGE_LIKELY"]
    return X, y, df


def train_and_cache_model():
    df = _load_storm_events()
    if df.empty:
        return None
    X, y, df_full = _prepare_training_data(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = GradientBoostingClassifier(random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    probas = model.predict_proba(X_test)[:, 1]
    df_full["OUTAGE_PROB"] = model.predict_proba(X)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, probas)
    cal_true, cal_pred = calibration_curve(y_test, probas, n_bins=10, strategy="uniform")

    stability = (
        df_full.groupby("YEAR")
        .agg(mean_pred=("OUTAGE_PROB", "mean"), mean_actual=("POWER_OUTAGE_LIKELY", "mean"))
        .reset_index()
        .sort_values("YEAR")
    )

    metrics = {
        "auc": float(roc_auc_score(y_test, probas)),
        "accuracy": float(accuracy_score(y_test, preds)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "calibration": {"predicted": cal_pred.tolist(), "observed": cal_true.tolist()},
        "stability": stability.to_dict(orient="records"),
    }
    joblib.dump({"model": model, "columns": X.columns.tolist()}, MODEL_PATH)
    with open(METRICS_PATH, "w") as handle:
        json.dump(metrics, handle)

    # Score each event to create county-level risk
    county_scores = (
        df_full.groupby(["FIPS", "STATE"])
        .agg(risk=("OUTAGE_PROB", "mean"), svi=("SVI_SCORE", "mean"))
        .reset_index()
        .rename(columns={"FIPS": "fips"})
    )
    county_scores["risk"] = county_scores["risk"].round(4)
    county_scores["svi"] = county_scores["svi"].fillna(0).round(4)

    # Ensure coverage for all counties using SVI baseline.
    svi = _load_svi()
    if not svi.empty:
        svi = svi[["FIPS", "COUNTY", "STATE", "ST_ABBR", "RPL_THEMES"]].rename(
            columns={
                "FIPS": "fips",
                "COUNTY": "county",
                "STATE": "state_name",
                "ST_ABBR": "state_abbr",
                "RPL_THEMES": "svi",
            }
        )
        svi["fips"] = svi["fips"].str.zfill(5)
        svi["svi"] = svi["svi"].fillna(0).round(4)
        svi["risk"] = svi["svi"]
        county_scores = svi.merge(
            county_scores[["fips", "risk"]].rename(columns={"risk": "ml_risk"}),
            on="fips",
            how="left",
        )
        county_scores["ml_risk"] = county_scores["ml_risk"].fillna(0)
        county_scores["risk"] = (0.7 * county_scores["ml_risk"] + 0.3 * county_scores["svi"]).round(4)
    county_scores.to_csv(COUNTY_RISK_PATH, index=False)
    return model


def load_model_bundle():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    train_and_cache_model()
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None


def get_county_risk():
    if not os.path.exists(COUNTY_RISK_PATH):
        train_and_cache_model()
    if not os.path.exists(COUNTY_RISK_PATH):
        return pd.DataFrame()
    df = pd.read_csv(COUNTY_RISK_PATH, dtype={"fips": str})
    df["fips"] = df["fips"].str.zfill(5)
    if "county" not in df.columns or "state_abbr" not in df.columns:
        svi = _load_svi()
        if not svi.empty:
            svi = svi[["FIPS", "COUNTY", "STATE", "ST_ABBR"]].rename(
                columns={
                    "FIPS": "fips",
                    "COUNTY": "county",
                    "STATE": "state_name",
                    "ST_ABBR": "state_abbr",
                }
            )
            df = df.merge(svi, on="fips", how="left")
    return df


def get_model_metrics():
    if not os.path.exists(METRICS_PATH):
        train_and_cache_model()
    if not os.path.exists(METRICS_PATH):
        return {}
    with open(METRICS_PATH, "r") as handle:
        return json.load(handle)


def get_model_evaluation():
    metrics = get_model_metrics()
    return {
        "roc_curve": metrics.get("roc_curve", {}),
        "calibration": metrics.get("calibration", {}),
        "stability": metrics.get("stability", []),
    }


def get_risk_for_county(fips):
    df = get_county_risk()
    if df.empty:
        return 0.0
    row = df[df["fips"] == str(fips)]
    if row.empty:
        return 0.0
    return float(row.iloc[0]["risk"])


def get_svi_for_county(fips):
    df = get_county_risk()
    if df.empty:
        return 0.0
    row = df[df["fips"] == str(fips)]
    if row.empty:
        return 0.0
    return float(row.iloc[0].get("svi", 0))
