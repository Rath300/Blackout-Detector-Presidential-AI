"""
EIA Form 860 (February 2026) operating generator data loader.
Aggregates 27k+ generators to county-level capacity and fuel-mix statistics.
"""
import os

import numpy as np
import pandas as pd

EIA_XLSX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "february_generator2026.xlsx",
)

# Map EIA energy source codes → simplified fuel category
FUEL_MAP = {
    # Solar
    "SUN": "solar",
    # Wind
    "WND": "wind",
    # Hydro
    "WAT": "hydro",
    # Nuclear
    "NUC": "nuclear",
    # Natural Gas
    "NG": "gas", "LFG": "gas", "OG": "gas", "BFG": "gas", "SGC": "gas",
    # Coal
    "BIT": "coal", "SUB": "coal", "LIG": "coal", "ANT": "coal", "RC": "coal",
    # Oil / Petroleum
    "DFO": "oil", "RFO": "oil", "JF": "oil", "KER": "oil", "PC": "oil",
    # Other fossil
    "WO": "fossil_other", "OOG": "fossil_other",
    # Storage
    "MWH": "storage", "FLW": "storage",
    # Biomass / other renewables
    "WDS": "biomass", "OBG": "biomass", "BLQ": "biomass", "MSW": "biomass", "AB": "biomass",
    # Geothermal
    "GEO": "geo",
}

# Combined fossil category
FOSSIL_CODES = {"gas", "coal", "oil", "fossil_other"}

_GEN_CACHE: dict = {}


def load_generators() -> pd.DataFrame:
    """Load EIA 860 operating generators. Returns raw DataFrame."""
    if _GEN_CACHE.get("raw") is not None:
        return _GEN_CACHE["raw"]

    if not os.path.exists(EIA_XLSX_PATH):
        return pd.DataFrame()

    try:
        df = pd.read_excel(EIA_XLSX_PATH, sheet_name="Operating", header=2)
    except Exception:
        return pd.DataFrame()

    df = df.rename(columns={
        "Plant State": "state_abbr",
        "County": "county_name",
        "Latitude": "lat",
        "Longitude": "lon",
        "Technology": "technology",
        "Energy Source Code": "fuel_code",
        "Net Summer Capacity (MW)": "summer_mw",
        "Nameplate Capacity (MW)": "nameplate_mw",
    })

    # Clean up
    df["summer_mw"] = pd.to_numeric(df.get("summer_mw"), errors="coerce").fillna(0)
    df["nameplate_mw"] = pd.to_numeric(df.get("nameplate_mw"), errors="coerce").fillna(0)
    df["mw"] = df["summer_mw"].where(df["summer_mw"] > 0, df["nameplate_mw"])
    df["fuel_code"] = df["fuel_code"].astype(str).str.strip()
    df["fuel_cat"] = df["fuel_code"].map(FUEL_MAP).fillna("other")
    df["state_abbr"] = df["state_abbr"].astype(str).str.strip().str.upper()
    df["county_name"] = df["county_name"].astype(str).str.strip().str.lower()

    _GEN_CACHE["raw"] = df
    return df


def _build_state_county_fips_lookup() -> dict:
    """Build (state_abbr, clean_county) → fips lookup from SVI data."""
    svi_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "svi_interactive_map.csv",
    )
    if not os.path.exists(svi_path):
        return {}
    svi = pd.read_csv(svi_path, dtype={"FIPS": str})
    svi["FIPS"] = svi["FIPS"].str.zfill(5)
    # Normalise county names: lowercase, strip " county" / " parish" / " borough"
    svi["county_clean"] = (
        svi["COUNTY"]
        .str.lower()
        .str.replace(r"\s+(county|parish|borough|census area|municipality|city and borough|unified government|city|consolidated government|metro government)$",
                     "", regex=True)
        .str.strip()
    )
    svi["state_abbr"] = svi["ST_ABBR"].str.upper()
    lookup = dict(zip(
        zip(svi["state_abbr"], svi["county_clean"]),
        svi["FIPS"]
    ))
    return lookup


def get_county_generation_profile() -> pd.DataFrame:
    """
    Aggregate EIA generators to county FIPS level.
    Returns DataFrame with columns:
      fips, total_mw, solar_mw, wind_mw, hydro_mw, nuclear_mw,
      gas_mw, coal_mw, oil_mw, fossil_mw, fossil_pct, renewable_pct,
      n_generators, has_nuclear, dominant_source
    """
    if _GEN_CACHE.get("county") is not None:
        return _GEN_CACHE["county"]

    df = load_generators()
    if df.empty:
        return pd.DataFrame()

    lookup = _build_state_county_fips_lookup()
    if not lookup:
        return pd.DataFrame()

    # Clean county name for matching
    df["county_clean"] = (
        df["county_name"]
        .str.replace(r"\s+(county|parish|borough|census area|city)$", "", regex=True)
        .str.strip()
    )
    df["fips"] = df.apply(
        lambda r: lookup.get((r["state_abbr"], r["county_clean"])), axis=1
    )
    df = df.dropna(subset=["fips"])
    df["fips"] = df["fips"].str.zfill(5)

    # Aggregate by county
    fuel_cats = ["solar", "wind", "hydro", "nuclear", "gas", "coal", "oil", "storage", "biomass", "geo"]
    agg: dict = {"mw": "sum", "fuel_code": "count"}
    result = df.groupby("fips").agg(total_mw=("mw", "sum"), n_generators=("fuel_code", "count")).reset_index()

    for cat in fuel_cats:
        sub = df[df["fuel_cat"] == cat].groupby("fips")["mw"].sum().reset_index().rename(columns={"mw": f"{cat}_mw"})
        result = result.merge(sub, on="fips", how="left")
        result[f"{cat}_mw"] = result[f"{cat}_mw"].fillna(0)

    result["fossil_mw"] = result["gas_mw"] + result["coal_mw"] + result["oil_mw"]
    result["renewable_mw"] = result["solar_mw"] + result["wind_mw"] + result["hydro_mw"] + result["geo_mw"]
    result["total_mw"] = result["total_mw"].clip(lower=0.001)
    result["fossil_pct"] = (result["fossil_mw"] / result["total_mw"]).clip(0, 1)
    result["renewable_pct"] = (result["renewable_mw"] / result["total_mw"]).clip(0, 1)
    result["has_nuclear"] = (result["nuclear_mw"] > 0).astype(int)
    result["log_total_mw"] = np.log1p(result["total_mw"])

    # Dominant source label
    source_cols = {c: c.replace("_mw", "") for c in ["solar_mw", "wind_mw", "hydro_mw", "nuclear_mw", "gas_mw", "coal_mw", "oil_mw"]}
    result["dominant_source"] = result[list(source_cols.keys())].idxmax(axis=1).map(source_cols)

    _GEN_CACHE["county"] = result
    return result


def get_generation_for_county(fips: str) -> dict:
    """Return generation profile dict for a single county FIPS."""
    profile = get_county_generation_profile()
    if profile.empty:
        return {}
    row = profile[profile["fips"] == str(fips).zfill(5)]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "total_mw":      round(float(r.get("total_mw", 0)), 1),
        "fossil_mw":     round(float(r.get("fossil_mw", 0)), 1),
        "fossil_pct":    round(float(r.get("fossil_pct", 0)), 3),
        "solar_mw":      round(float(r.get("solar_mw", 0)), 1),
        "wind_mw":       round(float(r.get("wind_mw", 0)), 1),
        "hydro_mw":      round(float(r.get("hydro_mw", 0)), 1),
        "nuclear_mw":    round(float(r.get("nuclear_mw", 0)), 1),
        "gas_mw":        round(float(r.get("gas_mw", 0)), 1),
        "coal_mw":       round(float(r.get("coal_mw", 0)), 1),
        "n_generators":  int(r.get("n_generators", 0)),
        "dominant_source": str(r.get("dominant_source", "unknown")),
        "renewable_pct": round(float(r.get("renewable_pct", 0)), 3),
    }
