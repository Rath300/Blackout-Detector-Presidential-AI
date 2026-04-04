"""
Risk engine — combines weather, outage, anomaly, ML model, NRI hazard scores,
and EIA generation mix into a single blackout risk score.
"""

SOURCE_PROFILES = {
    "solar":  {"label": "Solar PV",        "base": 0.00, "demand_f": 0.75},
    "wind":   {"label": "Wind Turbine",    "base": 0.01, "demand_f": 0.80},
    "hydro":  {"label": "Hydropower",      "base": 0.02, "demand_f": 0.85},
    "fossil": {"label": "Fossil Fuel",     "base": 0.03, "demand_f": 1.08},
    "gas":    {"label": "Natural Gas",     "base": 0.03, "demand_f": 1.08},
    "coal":   {"label": "Coal Plant",      "base": 0.04, "demand_f": 1.05},
    "grid":   {"label": "Grid/Substation", "base": 0.02, "demand_f": 0.95},
}


def calculate_blackout_risk(
    weather_summary,
    outage_summary,
    anomaly_summary=None,
    facility_type=None,
    ml_risk=0,
    sensitivity=1.0,
    energy_source=None,
    nri_profile=None,       # dict from nri_data.get_county_nri()
    gen_profile=None,       # dict from generator_data.get_generation_for_county()
):
    weather_risk  = weather_summary.get("weather_risk", 0)
    outage_risk   = outage_summary.get("outage_risk", 0)
    anomaly_risk  = anomaly_summary.get("anomaly_density", 0) if anomaly_summary else 0

    source = (energy_source or "grid").lower()
    profile = SOURCE_PROFILES.get(source, SOURCE_PROFILES["grid"])

    # ── NRI hazard bonus ───────────────────────────────────────────────────────
    nri_bonus = 0.0
    if nri_profile and nri_profile.get("hazards"):
        hazards = nri_profile["hazards"]
        if source == "wind":
            nri_bonus = hazards.get("Strong Wind", 0) * 0.15 + hazards.get("Hurricane", 0) * 0.10 + hazards.get("Tornado", 0) * 0.08
        elif source == "solar":
            nri_bonus = hazards.get("Wildfire", 0) * 0.12 + hazards.get("Heat Wave", 0) * 0.10
        elif source == "hydro":
            nri_bonus = hazards.get("Drought", 0) * 0.20 + hazards.get("Riverine Flooding", 0) * 0.08
        elif source in ("fossil", "gas"):
            nri_bonus = hazards.get("Heat Wave", 0) * 0.18 + hazards.get("Cold Wave", 0) * 0.12 + hazards.get("Ice Storm", 0) * 0.10
        elif source == "coal":
            nri_bonus = hazards.get("Heat Wave", 0) * 0.15 + hazards.get("Riverine Flooding", 0) * 0.10
        else:  # grid
            nri_bonus = (
                hazards.get("Strong Wind", 0) * 0.10 + hazards.get("Ice Storm", 0) * 0.10
                + hazards.get("Lightning", 0) * 0.08 + hazards.get("Wildfire", 0) * 0.08
            )
        nri_bonus = min(nri_bonus, 0.30)

    # ── Generation-mix bonus ───────────────────────────────────────────────────
    gen_bonus = 0.0
    if gen_profile:
        fossil_pct = gen_profile.get("fossil_pct", 0)
        # High fossil dependence + heat wave → demand spike risk
        if source in ("fossil", "gas", "grid"):
            max_t = weather_summary.get("max_temp_c", 20)
            if max_t > 35:
                gen_bonus = fossil_pct * min((max_t - 35) / 15, 1) * 0.15
        # Nuclear presence slightly reduces risk (stable baseload)
        if gen_profile.get("nuclear_mw", 0) > 0:
            gen_bonus -= 0.02
    gen_bonus = max(gen_bonus, 0)

    # ── Source-specific weather bonuses (kept small, capped) ──────────────────
    temp_stress = 0.0
    if source in {"fossil", "gas"}:
        max_t = weather_summary.get("max_temp_c", 20)
        min_t = weather_summary.get("min_temp_c", 15)
        if max_t > 38:
            temp_stress = min(0.08, (max_t - 38) / 25)
        elif min_t < -5:
            temp_stress = min(0.06, abs(min_t + 5) / 30)

    wind_curtailment = 0.0
    if source == "wind":
        if weather_summary.get("max_gust", 0) > 35:
            wind_curtailment = 0.10
        elif weather_summary.get("max_wind", 0) > 25:
            wind_curtailment = 0.05

    hydro_drought = 0.0
    if source == "hydro":
        hydro_drought = weather_summary.get("drought_score", 0) * 0.12

    solar_cloud = 0.0
    if source == "solar":
        solar_cloud = (weather_summary.get("avg_cloud_pct", 0) / 100.0) * 0.08

    # Total source adjustment capped at 0.12 so no single factor dominates
    source_adj = min(temp_stress + wind_curtailment + hydro_drought + solar_cloud, 0.12)

    # ── Facility conservatism ──────────────────────────────────────────────────
    facility_weight = 1.0
    if facility_type:
        ft = facility_type.lower()
        if ft in {"hospital", "ems", "emergency"}:
            facility_weight = 1.06
        elif ft in {"school", "shelter"}:
            facility_weight = 1.03

    # ── Combine ────────────────────────────────────────────────────────────────
    # Each input is already on a conservative 0–1 scale (weather 0.02–0.40,
    # outage 0.01–0.12, ml_risk 0.01–0.35). Weights intentionally don't sum to
    # 1.0 so the raw combined stays well under 0.20 for a normal day.
    combined = (
        0.35 * weather_risk
        + 0.20 * outage_risk
        + 0.15 * anomaly_risk
        + 0.20 * ml_risk
        + 0.04 * profile["base"]
        + 0.03 * nri_bonus
        + 0.02 * gen_bonus
        + source_adj * 0.50      # further dampen source-specific adjustments
    )
    combined *= profile["demand_f"]
    combined *= facility_weight
    combined *= sensitivity
    # Max realistic daily blackout risk even in severe conditions
    combined = min(round(combined, 4), 0.75)

    return {
        "blackout_risk": combined,
        "energy_source": source,
        "source_label":  profile["label"],
        "components": {
            "weather_risk":     weather_risk,
            "outage_risk":      outage_risk,
            "anomaly_risk":     anomaly_risk,
            "ml_risk":          ml_risk,
            "nri_bonus":        round(nri_bonus, 4),
            "gen_bonus":        round(gen_bonus, 4),
            "facility_weight":  facility_weight,
            "source_base":      profile["base"],
            "temp_stress":      round(temp_stress, 4),
            "wind_curtailment": round(wind_curtailment, 4),
            "hydro_drought":    round(hydro_drought, 4),
            "solar_cloud":      round(solar_cloud, 4),
        },
    }
