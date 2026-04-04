"""
ML risk model for county-level blackout probability.

Data sources:
  - NOAA Storm Events (all available years)
  - FEMA National Risk Index (NRI) per-county hazard scores
  - EIA Form 860 generator capacity mix per county
  - CDC SVI (fallback vulnerability layer)
"""
import glob
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.calibration import calibration_curve

from .nri_data import get_nri_feature_matrix
from .generator_data import get_county_generation_profile


# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR        = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
MODEL_PATH      = os.path.join(DATA_DIR, "risk_model.pkl")
COUNTY_RISK_PATH= os.path.join(DATA_DIR, "county_risk.csv")
METRICS_PATH    = os.path.join(DATA_DIR, "risk_model_metrics.json")
STORM_GLOB      = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "StormEvents_details-*.csv.gz")
SVI_PATH        = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "svi_interactive_map.csv")

OUTAGE_EVENT_TYPES = {
    "Thunderstorm Wind", "High Wind", "Hurricane", "Tornado",
    "Ice Storm", "Winter Storm", "Heavy Snow", "Blizzard",
    "Tropical Storm", "Flood", "Flash Flood", "Coastal Flood",
    "Extreme Cold/Wind Chill", "Heat", "Drought", "Wildfire",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _parse_damage(value):
    if pd.isna(value):
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    mult = 1.0
    if s[-1].upper() == "K":
        mult = 1_000.0; s = s[:-1]
    elif s[-1].upper() == "M":
        mult = 1_000_000.0; s = s[:-1]
    elif s[-1].upper() == "B":
        mult = 1_000_000_000.0; s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def _load_storm_events() -> pd.DataFrame:
    files = sorted(glob.glob(STORM_GLOB))
    if not files:
        return pd.DataFrame()
    frames = [pd.read_csv(p) for p in files]
    df = pd.concat(frames, ignore_index=True)
    return df


def _load_svi() -> pd.DataFrame:
    if not os.path.exists(SVI_PATH):
        return pd.DataFrame()
    df = pd.read_csv(SVI_PATH, dtype={"FIPS": str})
    df["FIPS"] = df["FIPS"].str.zfill(5)
    return df


# ── Training ───────────────────────────────────────────────────────────────────
def _prepare_training_data(df: pd.DataFrame):
    df = df.copy()
    df["STATE_FIPS_STR"]  = df["STATE_FIPS"].astype(str).str.zfill(2)
    df["COUNTY_FIPS_STR"] = df["CZ_FIPS"].astype(str).str.zfill(3)
    df["FIPS"]            = df["STATE_FIPS_STR"] + df["COUNTY_FIPS_STR"]

    # ── Legacy SVI merge (fallback) ───────────────────────────────────────────
    svi = _load_svi()
    if not svi.empty:
        svi_slim = svi[["FIPS", "RPL_THEMES"]].rename(columns={"RPL_THEMES": "SVI_SCORE"})
        df = df.merge(svi_slim, on="FIPS", how="left")
    else:
        df["SVI_SCORE"] = 0
    df["SVI_SCORE"] = df["SVI_SCORE"].fillna(0)

    # ── NRI county features ───────────────────────────────────────────────────
    nri = get_nri_feature_matrix()
    if not nri.empty:
        df = df.merge(nri[["fips"] + [c for c in nri.columns if c not in ("fips", "state_name_nri", "state_abbr_nri", "county_nri")]],
                      left_on="FIPS", right_on="fips", how="left")
    nri_cols = ["nri_risk", "nri_eal", "nri_sovi", "nri_resl",
                "SWND_NORM", "HRCN_NORM", "TRND_NORM", "HWAV_NORM", "CWAV_NORM",
                "ISTM_NORM", "DRGT_NORM", "WFIR_NORM", "LTNG_NORM", "RFLD_NORM"]
    for c in nri_cols:
        if c not in df.columns:
            df[c] = 0
    df[nri_cols] = df[nri_cols].fillna(0)

    # ── EIA generation mix features ───────────────────────────────────────────
    gen = get_county_generation_profile()
    if not gen.empty:
        gen_cols = ["fips", "fossil_pct", "renewable_pct", "has_nuclear", "log_total_mw"]
        df = df.merge(gen[gen_cols], left_on="FIPS", right_on="fips", how="left")
    for c in ["fossil_pct", "renewable_pct", "has_nuclear", "log_total_mw"]:
        if c not in df.columns:
            df[c] = 0
    df[["fossil_pct", "renewable_pct", "has_nuclear", "log_total_mw"]] = \
        df[["fossil_pct", "renewable_pct", "has_nuclear", "log_total_mw"]].fillna(0)

    # ── Storm-event damage features ───────────────────────────────────────────
    df["DAMAGE_PROPERTY_NUM"] = df["DAMAGE_PROPERTY"].apply(_parse_damage)
    df["DAMAGE_CROPS_NUM"]    = df["DAMAGE_CROPS"].apply(_parse_damage)
    df["INJURIES"]            = df["INJURIES_DIRECT"].fillna(0) + df["INJURIES_INDIRECT"].fillna(0)
    df["DEATHS"]              = df["DEATHS_DIRECT"].fillna(0)   + df["DEATHS_INDIRECT"].fillna(0)

    df["IS_OUTAGE_EVENT"] = df["EVENT_TYPE"].isin(OUTAGE_EVENT_TYPES).astype(int)
    df["POWER_OUTAGE_LIKELY"] = (
        (df["IS_OUTAGE_EVENT"] == 1)
        & ((df["DAMAGE_PROPERTY_NUM"] >= 500_000) | (df["INJURIES"] > 0) | (df["DEATHS"] > 0))
    ).astype(int)

    base_features = df[[
        "DAMAGE_PROPERTY_NUM", "DAMAGE_CROPS_NUM", "INJURIES", "DEATHS",
        "MAGNITUDE", "BEGIN_LAT", "BEGIN_LON", "SVI_SCORE",
    ]].fillna(0)

    nri_features  = df[nri_cols].fillna(0)
    eia_features  = df[["fossil_pct", "renewable_pct", "has_nuclear", "log_total_mw"]].fillna(0)
    event_dummies = pd.get_dummies(df["EVENT_TYPE"], prefix="event")

    X = pd.concat([base_features, nri_features, eia_features, event_dummies], axis=1)
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
    model = GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.08, max_depth=5,
        subsample=0.8, random_state=42
    )
    model.fit(X_train, y_train)
    preds  = model.predict(X_test)
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

    # Feature importance (top 20)
    feat_imp = dict(sorted(
        zip(X.columns.tolist(), model.feature_importances_.tolist()),
        key=lambda x: -x[1]
    )[:20])

    metrics = {
        "auc":            float(roc_auc_score(y_test, probas)),
        "accuracy":       float(accuracy_score(y_test, preds)),
        "train_rows":     int(len(X_train)),
        "test_rows":      int(len(X_test)),
        "feature_importance": feat_imp,
        "roc_curve":      {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "calibration":    {"predicted": cal_pred.tolist(), "observed": cal_true.tolist()},
        "stability":      stability.to_dict(orient="records"),
    }
    joblib.dump({"model": model, "columns": X.columns.tolist()}, MODEL_PATH)
    with open(METRICS_PATH, "w") as fh:
        json.dump(metrics, fh)

    # ── Build county risk scores ───────────────────────────────────────────────
    # ML storm probability per county
    county_ml = (
        df_full.groupby("FIPS")
        .agg(ml_risk=("OUTAGE_PROB", "mean"))
        .reset_index()
        .rename(columns={"FIPS": "fips"})
    )

    # Start from SVI for full coverage (3144 counties)
    svi = _load_svi()
    if not svi.empty:
        base = svi[["FIPS", "COUNTY", "STATE", "ST_ABBR", "RPL_THEMES"]].rename(columns={
            "FIPS": "fips", "COUNTY": "county", "STATE": "state_name",
            "ST_ABBR": "state_abbr", "RPL_THEMES": "svi",
        })
        base["fips"] = base["fips"].str.zfill(5)
        base["svi"]  = base["svi"].fillna(0).clip(0, 1)
    else:
        base = pd.DataFrame()

    # Merge ML storm risk
    if not base.empty:
        base = base.merge(county_ml, on="fips", how="left")
        base["ml_risk"] = base["ml_risk"].fillna(0)
    else:
        base = county_ml.copy()
        base["svi"] = 0

    # Merge NRI
    nri = get_nri_feature_matrix()
    if not nri.empty:
        base = base.merge(
            nri[["fips", "nri_risk", "nri_eal", "nri_sovi", "nri_resl"]
                + [f"{h}_NORM" for h in ["SWND", "HRCN", "TRND", "HWAV", "CWAV", "ISTM", "DRGT", "WFIR", "LTNG", "RFLD"]
                   if f"{h}_NORM" in nri.columns]],
            on="fips", how="left"
        )
        for c in ["nri_risk", "nri_eal", "nri_sovi", "nri_resl"]:
            base[c] = base.get(c, pd.Series(0)).fillna(0)

    # Merge EIA generation profile
    gen = get_county_generation_profile()
    if not gen.empty:
        base = base.merge(
            gen[["fips", "fossil_pct", "renewable_pct", "total_mw", "dominant_source",
                 "solar_mw", "wind_mw", "hydro_mw", "nuclear_mw", "gas_mw", "coal_mw", "n_generators"]],
            on="fips", how="left"
        )
        base["fossil_pct"] = base["fossil_pct"].fillna(0)

    # ── Composite risk score ───────────────────────────────────────────────────
    # NRI scores are percentile-rank uniform (0-1). Apply a power transform so
    # only truly extreme counties (top 10%) get a large NRI contribution.
    # Formula: power=1.8 → bottom 50% contribute <0.35, top 10% contribute >0.75
    nri_risk_col  = base["nri_risk"]  if "nri_risk"  in base.columns else pd.Series(0.25, index=base.index)
    nri_resl_col  = base["nri_resl"]  if "nri_resl"  in base.columns else pd.Series(0.5, index=base.index)
    nri_eal_col   = base["nri_eal"]   if "nri_eal"   in base.columns else pd.Series(0.25, index=base.index)

    nri_damped  = nri_risk_col.clip(0, 1) ** 1.8   # compress mid-range scores
    resl_damped = (1.0 - nri_resl_col.clip(0, 1)) ** 1.8
    eal_damped  = nri_eal_col.clip(0, 1) ** 1.8

    base["risk"] = (
        0.40 * base["ml_risk"].clip(0, 1)
        + 0.25 * nri_damped
        + 0.18 * base["svi"].clip(0, 1)
        + 0.10 * resl_damped
        + 0.07 * eal_damped
    ).round(4)

    # Scale to realistic daily blackout probability.
    # Most counties baseline: 2–6%. Genuinely high-risk: up to 35%.
    # The raw weighted sum centres near 0.25; multiply by 0.20 to rebase to ~0.05 mean.
    base["risk"] = (base["risk"] * 0.20).clip(0, 0.40).round(4)
    base.to_csv(COUNTY_RISK_PATH, index=False)
    return model


# ── Public API ─────────────────────────────────────────────────────────────────
def load_model_bundle():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    train_and_cache_model()
    return joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None


def get_county_risk() -> pd.DataFrame:
    if not os.path.exists(COUNTY_RISK_PATH):
        train_and_cache_model()
    if not os.path.exists(COUNTY_RISK_PATH):
        return pd.DataFrame()
    df = pd.read_csv(COUNTY_RISK_PATH, dtype={"fips": str})
    df["fips"] = df["fips"].str.zfill(5)
    return df


def get_model_metrics() -> dict:
    if not os.path.exists(METRICS_PATH):
        train_and_cache_model()
    if not os.path.exists(METRICS_PATH):
        return {}
    with open(METRICS_PATH) as fh:
        return json.load(fh)


def get_model_evaluation() -> dict:
    m = get_model_metrics()
    return {
        "roc_curve":   m.get("roc_curve", {}),
        "calibration": m.get("calibration", {}),
        "stability":   m.get("stability", []),
        "feature_importance": m.get("feature_importance", {}),
    }


def get_risk_for_county(fips: str) -> float:
    df = get_county_risk()
    if df.empty:
        return 0.0
    row = df[df["fips"] == str(fips).zfill(5)]
    return float(row.iloc[0]["risk"]) if not row.empty else 0.0


def get_svi_for_county(fips: str) -> float:
    df = get_county_risk()
    if df.empty:
        return 0.0
    row = df[df["fips"] == str(fips).zfill(5)]
    return float(row.iloc[0].get("svi", 0)) if not row.empty else 0.0
