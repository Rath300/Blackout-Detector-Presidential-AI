def calculate_blackout_risk(
    weather_summary,
    outage_summary,
    anomaly_summary=None,
    facility_type=None,
    ml_risk=0,
    sensitivity=1.0,
):
    weather_risk = weather_summary.get("weather_risk", 0)
    outage_risk = outage_summary.get("outage_risk", 0)
    anomaly_risk = 0
    if anomaly_summary:
        anomaly_risk = anomaly_summary.get("anomaly_density", 0)

    # Facility weighting: hospitals/EMS get a slight uptick to be conservative.
    facility_weight = 1.0
    if facility_type:
        if facility_type.lower() in {"hospital", "ems", "emergency"}:
            facility_weight = 1.1
        elif facility_type.lower() in {"school", "shelter"}:
            facility_weight = 1.05

    combined = 0.35 * weather_risk + 0.30 * outage_risk + 0.20 * anomaly_risk + 0.15 * ml_risk
    combined *= facility_weight
    combined *= sensitivity
    combined = min(round(combined, 4), 1.0)

    return {
        "blackout_risk": combined,
        "components": {
            "weather_risk": weather_risk,
            "outage_risk": outage_risk,
            "anomaly_risk": anomaly_risk,
            "ml_risk": ml_risk,
            "facility_weight": facility_weight,
        },
    }
