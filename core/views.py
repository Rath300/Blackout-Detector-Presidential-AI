import json
import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import anomaly as anomaly_service
from .services import ai_chat, alerting, ml_risk, outage_data, risk_engine, weather


def _parse_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _lookup_county_fips(lat, lon):
    response = requests.get(
        "https://geo.fcc.gov/api/census/area",
        params={"lat": lat, "lon": lon, "format": "json"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if not results:
        return None
    county_fips = results[0].get("county_fips")
    return county_fips


@csrf_exempt
def geocode(request):
    query = request.GET.get("query")
    if not query:
        return JsonResponse({"error": "Missing query parameter."}, status=400)

    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 3},
        headers={"User-Agent": "SolixaDemo/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    return JsonResponse({"results": response.json()})


@csrf_exempt
def weather_forecast(request):
    lat = _parse_float(request.GET.get("lat"))
    lon = _parse_float(request.GET.get("lon"))
    hours = _parse_int(request.GET.get("hours"), 72)
    if lat is None or lon is None:
        return JsonResponse({"error": "Missing lat/lon parameters."}, status=400)

    forecast = weather.get_open_meteo_forecast(lat, lon, hours=hours)
    alerts = weather.get_nws_alerts(lat, lon)
    summary = weather.summarize_weather_risk(forecast, alerts)
    return JsonResponse({"forecast": forecast, "alerts": alerts, "summary": summary})


@csrf_exempt
def weather_alerts(request):
    lat = _parse_float(request.GET.get("lat"))
    lon = _parse_float(request.GET.get("lon"))
    if lat is None or lon is None:
        return JsonResponse({"error": "Missing lat/lon parameters."}, status=400)
    alerts = weather.get_nws_alerts(lat, lon)
    return JsonResponse(alerts)


@csrf_exempt
def outage_history(request):
    state = request.GET.get("state")
    days = _parse_int(request.GET.get("days"), 365)
    summary = outage_data.summarize_outages(state, days=days)
    return JsonResponse(summary)


@csrf_exempt
def anomaly_score(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)

    df = None
    if request.FILES:
        upload = request.FILES.get("file")
        if upload:
            df = anomaly_service.load_inverter_csv(upload.read())
    else:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        records = payload.get("records") or payload.get("data")
        if records:
            df = anomaly_service.load_inverter_json(records)

    if df is None or df.empty:
        return JsonResponse({"error": "No valid inverter data provided."}, status=400)

    contamination = _parse_float(request.GET.get("contamination"), anomaly_service.DEFAULT_CONTAMINATION)
    scored = anomaly_service.detect_anomalies(df, contamination=contamination)

    anomaly_count = int(scored["anomaly"].sum())
    anomaly_density = round(anomaly_count / max(len(scored), 1), 4)

    sample = scored[scored["anomaly"]].head(10)[["TIME_STAMP", "Value"]]
    sample = sample.to_dict(orient="records")

    return JsonResponse(
        {
            "rows": int(len(scored)),
            "anomaly_count": anomaly_count,
            "anomaly_density": anomaly_density,
            "sample_anomalies": sample,
        }
    )


@csrf_exempt
def anomaly_sample(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_path = os.path.join(base_dir, "Anomaly_Data.csv")
    if not os.path.exists(sample_path):
        return JsonResponse({"error": "Sample inverter data not found."}, status=404)

    with open(sample_path, "rb") as handle:
        df = anomaly_service.load_inverter_csv(handle.read())

    if df is None or df.empty:
        return JsonResponse({"error": "Sample inverter data invalid."}, status=400)

    scored = anomaly_service.detect_anomalies(df, contamination=anomaly_service.DEFAULT_CONTAMINATION)
    anomaly_count = int(scored["anomaly"].sum())
    anomaly_density = round(anomaly_count / max(len(scored), 1), 4)
    sample = scored[scored["anomaly"]].head(10)[["TIME_STAMP", "Value"]]
    sample = sample.to_dict(orient="records")

    return JsonResponse(
        {
            "rows": int(len(scored)),
            "anomaly_count": anomaly_count,
            "anomaly_density": anomaly_density,
            "sample_anomalies": sample,
            "source": "Anomaly_Data.csv",
        }
    )


@csrf_exempt
def blackout_risk(request):
    lat = _parse_float(request.GET.get("lat"))
    lon = _parse_float(request.GET.get("lon"))
    state = request.GET.get("state")
    facility_type = request.GET.get("facilityType")
    anomaly_density = _parse_float(request.GET.get("anomalyDensity"), 0)
    sensitivity = _parse_float(request.GET.get("sensitivity"), 1.0) or 1.0
    if lat is None or lon is None:
        return JsonResponse({"error": "Missing lat/lon parameters."}, status=400)

    forecast = weather.get_open_meteo_forecast(lat, lon, hours=72)
    alerts = weather.get_nws_alerts(lat, lon)
    weather_summary = weather.summarize_weather_risk(forecast, alerts)
    outage_summary = outage_data.summarize_outages(state, days=365)

    anomaly_summary = {"anomaly_density": anomaly_density}
    county_fips = _lookup_county_fips(lat, lon)
    ml_county_risk = ml_risk.get_risk_for_county(county_fips) if county_fips else 0
    svi_score = ml_risk.get_svi_for_county(county_fips) if county_fips else 0
    risk = risk_engine.calculate_blackout_risk(
        weather_summary,
        outage_summary,
        anomaly_summary=anomaly_summary,
        facility_type=facility_type,
        ml_risk=ml_county_risk,
        sensitivity=sensitivity,
    )

    return JsonResponse(
        {
            "risk": risk,
            "weather_summary": weather_summary,
            "outage_summary": outage_summary,
            "county_fips": county_fips,
            "ml_county_risk": ml_county_risk,
            "svi_score": svi_score,
        }
    )


@csrf_exempt
def blackout_choropleth(request):
    state = request.GET.get("state")
    df = ml_risk.get_county_risk()
    if df.empty:
        return JsonResponse({"counties": []})

    if state:
        state = state.strip()
        if len(state) == 2 and "state_abbr" in df.columns:
            df = df[df["state_abbr"].str.upper() == state.upper()]
        elif "state_name" in df.columns:
            df = df[df["state_name"].str.upper() == state.upper()]
        elif "STATE" in df.columns:
            df = df[df["STATE"].str.upper() == state.upper()]

    counties = df.to_dict(orient="records")
    return JsonResponse({"counties": counties})


@csrf_exempt
def model_metrics(request):
    metrics = ml_risk.get_model_metrics()
    return JsonResponse({"metrics": metrics})


@csrf_exempt
def model_evaluation(request):
    evaluation = ml_risk.get_model_evaluation()
    return JsonResponse({"evaluation": evaluation})


@csrf_exempt
def county_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    county = payload.get("county", {})
    try:
        response_text = ai_chat.ask_county_summary(county)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"response": response_text})


@csrf_exempt
def alert_subscribe(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    return JsonResponse({"status": "ok", "subscription": payload})


@csrf_exempt
def alert_test(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    message = payload.get(
        "message",
        "Solixa alert test: high blackout risk detected for your area. Please review preparedness steps.",
    )
    to_number = payload.get("to_number")
    try:
        result = alerting.send_sms(message, to_number=to_number)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"status": "sent", "details": result})
