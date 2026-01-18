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


def summarize_outages(state, days=365):
    df = load_outage_data()
    if df.empty:
        return {"state": state, "incidents": 0, "customers_affected": 0, "outage_risk": 0.0}

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = df[df["date"] >= cutoff]
    if state:
        filtered = filtered[filtered["state"].str.upper() == state.upper()]

    incidents = int(len(filtered))
    customers = int(filtered["customers_affected"].sum()) if incidents else 0

    # Simple scaling for demo: 0-1 risk based on incidents and customer count
    incident_score = min(incidents / 5, 1)
    customer_score = min(customers / 100000, 1)
    outage_risk = round(0.6 * incident_score + 0.4 * customer_score, 4)

    return {
        "state": state.upper() if state else "ALL",
        "incidents": incidents,
        "customers_affected": customers,
        "outage_risk": outage_risk,
        "days": days,
    }
