import os
import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
NWS_HEADERS = {"User-Agent": os.environ.get("NWS_USER_AGENT", "SolixaDemo/1.0")}


def get_open_meteo_forecast(lat, lon, hours=72):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m",
        "forecast_hours": hours,
        "timezone": "UTC",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def get_nws_alerts(lat, lon):
    params = {"point": f"{lat},{lon}"}
    response = requests.get(NWS_ALERTS_URL, params=params, headers=NWS_HEADERS, timeout=15)
    response.raise_for_status()
    return response.json()


def summarize_weather_risk(forecast_json, alerts_json):
    hourly = forecast_json.get("hourly", {})
    winds = hourly.get("wind_speed_10m", []) or []
    gusts = hourly.get("wind_gusts_10m", []) or []
    precip = hourly.get("precipitation", []) or []

    max_wind = max(winds) if winds else 0
    max_gust = max(gusts) if gusts else 0
    max_precip = max(precip) if precip else 0

    alert_features = alerts_json.get("features", []) if alerts_json else []
    active_alerts = len(alert_features)

    # Simple heuristic risk score (0-1)
    wind_score = min(max(max_wind / 25, max_gust / 35), 1)
    precip_score = min(max_precip / 10, 1)
    alert_score = min(active_alerts / 3, 1)

    risk = 0.4 * wind_score + 0.3 * precip_score + 0.3 * alert_score
    return {
        "max_wind": max_wind,
        "max_gust": max_gust,
        "max_precip": max_precip,
        "active_alerts": active_alerts,
        "weather_risk": round(risk, 4),
    }
