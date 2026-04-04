"""
FEMA National Risk Index (NRI) county-level data loader.
Source: NRI_Table_Counties.zip (December 2025 release)
"""
import io
import os
import zipfile

import numpy as np
import pandas as pd

NRI_ZIP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "NRI_Table_Counties.zip",
)

# Hazard codes → human-readable names
HAZARD_META = {
    "AVLN": "Avalanche",
    "CFLD": "Coastal Flooding",
    "CWAV": "Cold Wave",
    "DRGT": "Drought",
    "ERQK": "Earthquake",
    "HAIL": "Hail",
    "HWAV": "Heat Wave",
    "HRCN": "Hurricane",
    "ISTM": "Ice Storm",
    "LNDS": "Landslide",
    "LTNG": "Lightning",
    "RFLD": "Riverine Flooding",
    "SWND": "Strong Wind",
    "TRND": "Tornado",
    "TSUN": "Tsunami",
    "WFIR": "Wildfire",
    "WNTW": "Winter Weather",
}

# Hazards most relevant to power-grid risk (used as ML features)
GRID_HAZARDS = ["SWND", "HRCN", "TRND", "HWAV", "CWAV", "ISTM", "DRGT", "WFIR", "LTNG", "RFLD"]

_NRI_CACHE: dict = {}


def load_nri() -> pd.DataFrame:
    """Load and cache NRI county data. Returns DataFrame indexed by 5-char FIPS."""
    if _NRI_CACHE.get("df") is not None:
        return _NRI_CACHE["df"]

    if not os.path.exists(NRI_ZIP_PATH):
        return pd.DataFrame()

    with zipfile.ZipFile(NRI_ZIP_PATH) as z:
        with z.open("NRI_Table_Counties.csv") as f:
            df = pd.read_csv(f, dtype={"STCOFIPS": str, "STATEFIPS": str, "COUNTYFIPS": str})

    df["fips"] = df["STCOFIPS"].str.zfill(5)

    # Normalize 0-100 scores to 0-1
    for col in ["RISK_SCORE", "EAL_SCORE", "SOVI_SCORE", "RESL_SCORE"]:
        if col in df.columns:
            df[col + "_NORM"] = pd.to_numeric(df[col], errors="coerce").fillna(50) / 100.0

    # Normalise per-hazard risk values (RISKV = dollar value → rank percentile → 0-1)
    for hazard in GRID_HAZARDS:
        col = f"{hazard}_RISKV"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
            # Use percentile rank so all hazards are on the same 0-1 scale
            df[f"{hazard}_NORM"] = vals.rank(pct=True).clip(0, 1)

    _NRI_CACHE["df"] = df
    return df


def get_county_nri(fips: str) -> dict:
    """Return NRI hazard profile for a single county FIPS."""
    df = load_nri()
    if df.empty:
        return {}
    row = df[df["fips"] == str(fips).zfill(5)]
    if row.empty:
        return {}
    r = row.iloc[0]
    out: dict = {
        "risk_score":     float(r.get("RISK_SCORE_NORM", 0)),
        "eal_score":      float(r.get("EAL_SCORE_NORM", 0)),
        "sovi_score":     float(r.get("SOVI_SCORE_NORM", 0)),
        "resilience":     float(r.get("RESL_SCORE_NORM", 0)),
        "risk_rating":    r.get("RISK_RATNG", ""),
        "population":     int(float(r.get("POPULATION", 0) or 0)),
        "build_value":    float(r.get("BUILDVALUE", 0) or 0),
        "hazards": {},
    }
    for hazard, label in HAZARD_META.items():
        norm_col = f"{hazard}_NORM"
        if norm_col in r.index:
            out["hazards"][label] = round(float(r.get(norm_col, 0) or 0), 4)
    return out


def get_nri_feature_matrix() -> pd.DataFrame:
    """
    Return a tidy per-county DataFrame with NRI features ready to merge with ML training data.
    Columns: fips, nri_risk, nri_eal, nri_sovi, nri_resl, + per-hazard NORM columns.
    """
    df = load_nri()
    if df.empty:
        return pd.DataFrame()

    keep = ["fips", "STATE", "STATEABBRV", "COUNTY", "POPULATION"]
    keep += ["RISK_SCORE_NORM", "EAL_SCORE_NORM", "SOVI_SCORE_NORM", "RESL_SCORE_NORM"]
    keep += [f"{h}_NORM" for h in GRID_HAZARDS if f"{h}_NORM" in df.columns]
    keep = [c for c in keep if c in df.columns]
    return df[keep].rename(columns={
        "RISK_SCORE_NORM": "nri_risk",
        "EAL_SCORE_NORM":  "nri_eal",
        "SOVI_SCORE_NORM": "nri_sovi",
        "RESL_SCORE_NORM": "nri_resl",
        "STATE":           "state_name_nri",
        "STATEABBRV":      "state_abbr_nri",
        "COUNTY":          "county_nri",
    })
