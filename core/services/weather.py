import os
import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
NWS_HEADERS = {"User-Agent": os.environ.get("NWS_USER_AGENT", "SolixaDemo/1.0")}

# Per energy-source weather risk weights: (wind, precip, cloud_cover, temp_extreme, nws_alert)
# Weights must roughly sum to 1.0 for interpretability.
SOURCE_WEATHER_WEIGHTS = {
    "solar":  (0.10, 0.15, 0.55, 0.10, 0.10),
    "wind":   (0.65, 0.10, 0.00, 0.15, 0.10),
    "hydro":  (0.10, 0.45, 0.00, 0.30, 0.15),
    "fossil": (0.10, 0.05, 0.00, 0.65, 0.20),
    "gas":    (0.10, 0.05, 0.00, 0.65, 0.20),
    "grid":   (0.30, 0.20, 0.10, 0.25, 0.15),
}
DEFAULT_WEIGHTS = (0.35, 0.20, 0.10, 0.20, 0.15)


def get_open_meteo_forecast(lat, lon, hours=72):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": (
            "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m,"
            "cloudcover,soil_moisture_0_to_1cm"
        ),
        "forecast_hours": hours,
        "timezone": "UTC",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def get_nws_alerts(lat, lon):
    params = {"point": f"{lat},{lon}"}
    try:
        response = requests.get(NWS_ALERTS_URL, params=params, headers=NWS_HEADERS, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception:
        # NWS frequently times out — return empty alerts rather than crashing
        return {"features": []}


def summarize_weather_risk(forecast_json, alerts_json, energy_source=None):
    hourly = forecast_json.get("hourly", {})
    winds  = hourly.get("wind_speed_10m", []) or []
    gusts  = hourly.get("wind_gusts_10m", []) or []
    precip = hourly.get("precipitation", []) or []
    clouds = hourly.get("cloudcover", []) or []
    temps  = hourly.get("temperature_2m", []) or []

    max_wind      = max(winds)  if winds  else 0.0
    max_gust      = max(gusts)  if gusts  else 0.0
    total_precip  = sum(precip) if precip else 0.0
    max_precip    = max(precip) if precip else 0.0
    avg_cloud     = (sum(clouds) / len(clouds)) if clouds else 0.0
    min_temp      = min(temps)  if temps  else 15.0
    max_temp      = max(temps)  if temps  else 20.0

    alert_features = (alerts_json.get("features", []) if alerts_json else [])
    active_alerts  = len(alert_features)

    # ── Normalised component scores (0–1) ────────────────────────────────────
    # Thresholds calibrated so normal conditions score near 0, severe events near 1
    # Wind: 0 at <20 km/h, 1.0 at 80 km/h gusts (genuine storm-force)
    wind_score  = min(max(max(max_wind - 20, 0) / 60.0, max(max_gust - 25, 0) / 55.0), 1.0)
    # Precip: 0 at <5 mm/hr, 1.0 at 50 mm/hr (heavy thunderstorm)
    precip_score = min(max(max_precip - 5, 0) / 45.0, 1.0)
    # Cloud cover only matters for solar; for grid it's minor — keep proportional but scaled
    cloud_score  = avg_cloud / 100.0

    # Temperature extreme: heat above 35°C or freeze below -5°C
    heat_risk    = max(0.0, (max_temp - 35.0) / 15.0)
    freeze_risk  = max(0.0, (-5.0 - min_temp)  / 20.0)
    temp_score   = min(max(heat_risk, freeze_risk), 1.0)

    alert_score  = min(active_alerts / 3.0, 1.0)

    # Drought proxy: only meaningful for hydro; requires extended dry spell (>20 mm threshold)
    drought_score = max(0.0, 1.0 - total_precip / 20.0) * 0.6

    # ── Source-aware aggregation ─────────────────────────────────────────────
    source = (energy_source or "grid").lower()
    w_wind, w_precip, w_cloud, w_temp, w_alert = SOURCE_WEATHER_WEIGHTS.get(source, DEFAULT_WEIGHTS)

    if source == "hydro":
        # Replace part of precip weight with drought (low rain = low reservoir)
        risk = (
            w_wind  * wind_score
            + 0.25  * drought_score
            + w_precip * precip_score
            + w_temp  * temp_score
            + w_alert * alert_score
        )
    else:
        risk = (
            w_wind  * wind_score
            + w_precip * precip_score
            + w_cloud  * cloud_score
            + w_temp  * temp_score
            + w_alert * alert_score
        )

    return {
        "max_wind":        round(max_wind, 1),
        "max_gust":        round(max_gust, 1),
        "max_precip":      round(max_precip, 2),
        "total_precip_72h": round(total_precip, 2),
        "avg_cloud_pct":   round(avg_cloud, 1),
        "min_temp_c":      round(min_temp, 1),
        "max_temp_c":      round(max_temp, 1),
        "active_alerts":   active_alerts,
        "drought_score":   round(drought_score, 4),
        # Scale down: raw component sum uses weights ~1.0, but typical day should score 0.02–0.08
        "weather_risk":    round(min(risk * 0.45, 1.0), 4),
        "energy_source":   source,
        "component_scores": {
            "wind":          round(wind_score, 3),
            "precipitation": round(precip_score, 3),
            "cloud_cover":   round(cloud_score, 3),
            "temperature":   round(temp_score, 3),
            "nws_alerts":    round(alert_score, 3),
            "drought":       round(drought_score, 3),
        },
    }
