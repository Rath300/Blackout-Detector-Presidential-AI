from django.urls import path

from . import views


urlpatterns = [
    path("geocode", views.geocode, name="geocode"),
    path("weather/forecast", views.weather_forecast, name="weather_forecast"),
    path("weather/alerts", views.weather_alerts, name="weather_alerts"),
    path("outages/history", views.outage_history, name="outage_history"),
    path("anomalies/score", views.anomaly_score, name="anomaly_score"),
    path("anomalies/sample", views.anomaly_sample, name="anomaly_sample"),
    path("blackout/risk", views.blackout_risk, name="blackout_risk"),
    path("blackout/choropleth", views.blackout_choropleth, name="blackout_choropleth"),
    path("model/metrics", views.model_metrics, name="model_metrics"),
    path("model/evaluation", views.model_evaluation, name="model_evaluation"),
    path("chat/county", views.county_chat, name="county_chat"),
    path("alerts/subscribe", views.alert_subscribe, name="alert_subscribe"),
    path("alerts/test", views.alert_test, name="alert_test"),
]
