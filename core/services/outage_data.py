import os
from datetime import datetime, timedelta

import pandas as pd


SAMPLE_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "oe417_sample.csv")


def load_outage_data():
    if not os.path.exists(SAMPLE_DATA_PATH):
        return pd.DataFrame()
    df = pd.read_csv(SAMPLE_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date"])


def summarize_outages(state, days=730):
    df = load_outage_data()
    if df.empty:
        return {"state": state, "incidents": 0, "customers_affected": 0, "outage_risk": 0.1}

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = df[df["date"] >= cutoff]
    if state:
        state_filtered = filtered[filtered["state"].str.upper() == state.upper()]
        if not state_filtered.empty:
            filtered = state_filtered
        else:
            # Unknown state → return a low baseline rather than inflating with all-state data
            return {"state": state.upper(), "incidents": 0, "customers_affected": 0, "outage_risk": 0.12, "days": days}

    incidents = int(len(filtered))
    customers = int(filtered["customers_affected"].sum()) if incidents else 0

    # Scale so typical state (2–5 incidents, ~200k customers over 2 years) gives ~0.05–0.12
    # Max score (20+ incidents, 2M+ customers) → 0.35
    incident_score = min(incidents / 30, 1.0)           # normalise at 30 incidents
    customer_score = min(customers / 2_000_000, 1.0)    # normalise at 2M customers
    outage_risk = round((0.55 * incident_score + 0.45 * customer_score) * 0.35, 4)

    return {
        "state": state.upper() if state else "ALL",
        "incidents": incidents,
        "customers_affected": customers,
        "outage_risk": outage_risk,
        "days": days,
    }
