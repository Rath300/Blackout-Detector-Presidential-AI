"use client"

import { useMemo, useRef, useState, useEffect } from "react"
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMapEvents } from "react-leaflet"
import type { GeoJsonObject } from "geojson"
import "leaflet/dist/leaflet.css"
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
} from "recharts"

import TextCursorProximity from "@/components/ui/text-cursor-proximity"
import { FileUpload } from "@/components/ui/file-upload"
import MorphPanel from "@/components/ui/ai-input"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { SpotlightNav } from "@/components/ui/spotlight-button"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1"

const emergencyAreas = [
  { name: "UCSF Medical Center", type: "hospital", lat: 37.7631, lon: -122.4586 },
  { name: "SF EMS Station 1", type: "ems", lat: 37.7946, lon: -122.3999 },
  { name: "Lowell High School", type: "school", lat: 37.7325, lon: -122.4856 },
  { name: "SOMA Shelter", type: "shelter", lat: 37.7786, lon: -122.4062 },
]

type RiskItem = {
  name: string
  type: string
  risk?: number
}

type CountyRisk = {
  fips: string
  risk: number
  county?: string
  state_abbr?: string
  state_name?: string
}

export default function App() {
  const heroRef = useRef<HTMLDivElement>(null)
  const riskMapRef = useRef<HTMLDivElement>(null)
  const inverterRef = useRef<HTMLDivElement>(null)
  const alertsRef = useRef<HTMLDivElement>(null)
  const modelRef = useRef<HTMLDivElement>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [stateCode, setStateCode] = useState("")
  const [mapCenter, setMapCenter] = useState<[number, number]>([39.8283, -98.5795])
  const [selectedLocation, setSelectedLocation] = useState("United States")
  const [geoJson, setGeoJson] = useState<GeoJsonObject | null>(null)
  const [riskByFips, setRiskByFips] = useState<Record<string, number>>({})
  const [anomalyDensity, setAnomalyDensity] = useState(0)
  const [anomalySummary, setAnomalySummary] = useState("No inverter data loaded yet.")
  const [anomalySamples, setAnomalySamples] = useState<
    { TIME_STAMP: string; Value: number }[]
  >([])
  const [facilityRisk, setFacilityRisk] = useState<string>("Run a risk check to see details.")
  const [areaSummary, setAreaSummary] = useState<string>("Select a location to see risk details.")
  const [smsStatus, setSmsStatus] = useState("")
  const [autoRiskRows, setAutoRiskRows] = useState<RiskItem[]>([])
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [alertSummary, setAlertSummary] = useState<string>("No alert data loaded yet.")
  const [alertGeoJson, setAlertGeoJson] = useState<GeoJsonObject | null>(null)
  const [facilityRiskMap, setFacilityRiskMap] = useState<Record<string, number>>({})
  const [modelMetrics, setModelMetrics] = useState<string>("Model metrics not loaded yet.")
  const [evaluationData, setEvaluationData] = useState<any>(null)
  const [countyDetails, setCountyDetails] = useState<Record<string, CountyRisk>>({})
  const [selectedCounty, setSelectedCounty] = useState<CountyRisk | null>(null)
  const [chatResponse, setChatResponse] = useState("Select a county to get AI guidance.")
  const [riskSensitivity, setRiskSensitivity] = useState(1.0)

  const riskLegend = useMemo(
    () => [
      { label: "0-15%", color: "#22c55e" },
      { label: "15-30%", color: "#4ade80" },
      { label: "30-50%", color: "#facc15" },
      { label: "50-70%", color: "#f97316" },
      { label: "70%+", color: "#dc2626" },
    ],
    []
  )

  const handleGeocode = async () => {
    if (!searchQuery) return
    const res = await fetch(`${API_BASE}/geocode?query=${encodeURIComponent(searchQuery)}`)
    if (!res.ok) return
    const data = await res.json()
    const first = data.results?.[0]
    if (first) {
      setMapCenter([parseFloat(first.lat), parseFloat(first.lon)])
      setSelectedLocation(first.display_name)
    }
  }

  const loadCountyRisk = async () => {
    const [riskRes, geoRes] = await Promise.all([
      fetch(
        `${API_BASE}/blackout/choropleth${
          stateCode ? `?state=${encodeURIComponent(stateCode)}` : ""
        }`
      ),
      fetch("https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"),
    ])
    if (!riskRes.ok || !geoRes.ok) return
    const riskPayload = await riskRes.json()
    const geoPayload = await geoRes.json()
    const nextRisk: Record<string, number> = {}
    const nextDetails: Record<string, CountyRisk> = {}
    riskPayload.counties?.forEach((row: CountyRisk) => {
      const fips = String(row.fips).padStart(5, "0")
      nextRisk[fips] = row.risk
      nextDetails[fips] = { ...row, fips }
    })
    setRiskByFips(nextRisk)
    setCountyDetails(nextDetails)
    setGeoJson(geoPayload)
  }

  const scoreInverterData = async (files: File[]) => {
    const file = files[0]
    if (!file) return
    const formData = new FormData()
    formData.append("file", file)
    const res = await fetch(`${API_BASE}/anomalies/score`, {
      method: "POST",
      body: formData,
    })
    const data = await res.json()
    if (!res.ok) {
      setAnomalySummary(data.error || "Could not score inverter data.")
      return
    }
    setAnomalyDensity(data.anomaly_density)
    setAnomalySummary(
      `Analyzed ${data.rows} rows · ${data.anomaly_count} anomalies · density ${(data.anomaly_density * 100).toFixed(2)}%`
    )
    setAnomalySamples(data.sample_anomalies || [])
  }

  const loadSampleInverterData = async () => {
    const res = await fetch(`${API_BASE}/anomalies/sample`, { method: "POST" })
    const data = await res.json()
    if (!res.ok) {
      setAnomalySummary(data.error || "Could not load sample data.")
      return
    }
    setAnomalyDensity(data.anomaly_density)
    setAnomalySummary(
      `Sample ${data.source}: ${data.rows} rows · ${data.anomaly_count} anomalies · density ${(data.anomaly_density * 100).toFixed(2)}%`
    )
    setAnomalySamples(data.sample_anomalies || [])
  }

  const checkFacilityRisk = async () => {
    const [lat, lon] = mapCenter
    const res = await fetch(
      `${API_BASE}/blackout/risk?lat=${lat}&lon=${lon}&facilityType=hospital&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}`
    )
    const data = await res.json()
    if (!res.ok) {
      setFacilityRisk(data.error || "Risk check failed.")
      return
    }
    const breakdown = data.risk.components
    setFacilityRisk(
      `Overall risk ${(data.risk.blackout_risk * 100).toFixed(1)}% · Weather ${(
        breakdown.weather_risk * 100
      ).toFixed(1)}% · Outage ${(breakdown.outage_risk * 100).toFixed(
        1
      )}% · Anomaly ${(breakdown.anomaly_risk * 100).toFixed(
        1
      )}% · ML ${(breakdown.ml_risk * 100).toFixed(1)}% · SVI ${(data.svi_score * 100).toFixed(1)}%`
    )
  }

  const refreshAreaSummary = async () => {
    const [lat, lon] = mapCenter
    const res = await fetch(
      `${API_BASE}/blackout/risk?lat=${lat}&lon=${lon}&facilityType=community&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}`
    )
    const data = await res.json()
    if (!res.ok) {
      setAreaSummary(data.error || "Could not load area summary.")
      return
    }
    const breakdown = data.risk.components
    setAreaSummary(
      `Risk ${(data.risk.blackout_risk * 100).toFixed(1)}% · Weather ${(
        breakdown.weather_risk * 100
      ).toFixed(1)}% · Outage ${(breakdown.outage_risk * 100).toFixed(
        1
      )}% · ML ${(breakdown.ml_risk * 100).toFixed(1)}% · SVI ${(data.svi_score * 100).toFixed(1)}%`
    )
  }

  const refreshWeatherAlerts = async () => {
    const [lat, lon] = mapCenter
    const res = await fetch(`${API_BASE}/weather/alerts?lat=${lat}&lon=${lon}`)
    const data = await res.json()
    if (!res.ok) {
      setAlertSummary(data.error || "Could not load alerts.")
      setAlertGeoJson(null)
      return
    }
    const features = data.features || []
    setAlertSummary(
      features.length
        ? `Active alerts: ${features.length} · ${features
            .slice(0, 2)
            .map((f: any) => f.properties?.event)
            .filter(Boolean)
            .join(", ")}`
        : "No active alerts near this location."
    )
    setAlertGeoJson(data)
  }

  const autoScoreEmergencyAreas = async () => {
    const rows: RiskItem[] = []
    for (const area of emergencyAreas) {
      const res = await fetch(
        `${API_BASE}/blackout/risk?lat=${area.lat}&lon=${area.lon}&facilityType=${area.type}&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}`
      )
      const data = await res.json()
      if (res.ok) {
        rows.push({ name: area.name, type: area.type, risk: data.risk.blackout_risk })
      } else {
        rows.push({ name: area.name, type: area.type, risk: undefined })
      }
    }
    setAutoRiskRows(rows)
    const nextMap: Record<string, number> = {}
    rows.forEach((row) => {
      if (row.risk !== undefined) {
        nextMap[row.name] = row.risk
      }
    })
    setFacilityRiskMap(nextMap)
  }

  useEffect(() => {
    if (!autoRefresh) return
    autoScoreEmergencyAreas()
    const timer = window.setInterval(autoScoreEmergencyAreas, 300000)
    return () => window.clearInterval(timer)
  }, [autoRefresh, anomalyDensity, riskSensitivity])

  useEffect(() => {
    refreshAreaSummary()
    refreshWeatherAlerts()
  }, [mapCenter, anomalyDensity, riskSensitivity])

  useEffect(() => {
    autoScoreEmergencyAreas()
  }, [])

  useEffect(() => {
    const loadMetrics = async () => {
      const res = await fetch(`${API_BASE}/model/metrics`)
      const data = await res.json()
      if (!res.ok || !data.metrics) {
        setModelMetrics("Model metrics unavailable.")
        return
      }
      const auc = data.metrics.auc ? (data.metrics.auc * 100).toFixed(1) : "N/A"
      const acc = data.metrics.accuracy ? (data.metrics.accuracy * 100).toFixed(1) : "N/A"
      setModelMetrics(`Model AUC ${auc}% · Accuracy ${acc}%`)
    }
    loadMetrics()
  }, [])

  useEffect(() => {
    const loadEvaluation = async () => {
      const res = await fetch(`${API_BASE}/model/evaluation`)
      const data = await res.json()
      if (!res.ok || !data.evaluation) return
      setEvaluationData(data.evaluation)
    }
    loadEvaluation()
  }, [])

  useEffect(() => {
    loadCountyRisk()
  }, [])

  const MapClickHandler = () => {
    useMapEvents({
      click: (event) => {
        setMapCenter([event.latlng.lat, event.latlng.lng])
        setSelectedLocation(`Lat ${event.latlng.lat.toFixed(4)}, Lon ${event.latlng.lng.toFixed(4)}`)
      },
    })
    return null
  }

  const sendSmsAlert = async () => {
    setSmsStatus("Sending alert...")
    const res = await fetch(`${API_BASE}/alerts/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message:
          "Solixa alert: elevated blackout risk detected. Review backup power and emergency plans.",
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      setSmsStatus(data.error || "SMS failed.")
      return
    }
    setSmsStatus(`Sent. Twilio status: ${data.details?.status ?? "queued"}`)
  }

  const requestCountyChat = async (prompt?: string) => {
    if (!selectedCounty) return
    setChatResponse("Generating guidance...")
    const res = await fetch(`${API_BASE}/chat/county`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        county: {
          fips: selectedCounty.fips,
          county: selectedCounty.county,
          state: selectedCounty.state_abbr || selectedCounty.state_name,
          risk: selectedCounty.risk,
          prompt,
        },
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      setChatResponse(data.error || "Chat failed.")
      return
    }
    setChatResponse(data.response || "No response.")
  }

  const handleNavigate = (label: string) => {
    const sections: Record<string, React.RefObject<HTMLDivElement>> = {
      Overview: heroRef,
      "Risk Map": riskMapRef,
      "Inverter Upload": inverterRef,
      Alerts: alertsRef,
      Settings: modelRef,
    }
    sections[label]?.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <div className="px-8 py-10">
      <div className="flex items-center justify-end">
        <SpotlightNav onNavigate={handleNavigate} />
      </div>

        <div
          ref={heroRef}
          className="mt-10 grid gap-8 rounded-3xl bg-white p-10 shadow-sm border border-emerald-100 md:grid-cols-[1.2fr_1fr]"
        >
          <div className="space-y-4">
            <TextCursorProximity
              label="Solixa Blackout Intelligence"
              className="text-3xl md:text-4xl font-semibold text-emerald-700"
              styles={{
                transform: {
                  from: "scale(1)",
                  to: "scale(1.05)",
                },
                color: {
                  from: "#16a34a",
                  to: "#14532d",
                },
              }}
              falloff="gaussian"
              radius={120}
              containerRef={heroRef}
            />
            <p className="text-slate-600 text-lg leading-relaxed">
              Automated blackout risk intelligence that merges real-time weather, outage
              history, inverter anomalies, and community vulnerability into a single
              operational view.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button onClick={checkFacilityRisk}>Run Local Risk Check</Button>
              <Button variant="outline" onClick={autoScoreEmergencyAreas}>
                Auto-score Emergency Areas
              </Button>
            </div>
            <p className="text-sm text-emerald-700">{facilityRisk}</p>
            <p className="text-xs text-slate-500">
              Active location: {selectedLocation}
            </p>
          </div>
          <img
            src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=1200&auto=format&fit=crop"
            alt="Community resilience"
            className="h-full w-full rounded-2xl object-cover"
          />
        </div>

        <div className="mt-10 grid gap-8 md:grid-cols-[2fr_1fr]">
          <div ref={riskMapRef} className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-100">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <h2 className="text-xl font-semibold text-emerald-700">Risk Map</h2>
              <div className="flex gap-2">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search city or address"
                />
                <Button variant="outline" onClick={handleGeocode}>
                  Search
                </Button>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Input
                value={stateCode}
                onChange={(e) => setStateCode(e.target.value.toUpperCase())}
                placeholder="State code (optional)"
                className="max-w-[180px]"
              />
              <Button onClick={loadCountyRisk}>Load County Risk</Button>
              <span className="text-xs text-slate-400">
                Leave blank for a full US heat map.
              </span>
            </div>
            <div className="mt-3 flex items-center gap-3 text-xs text-slate-500">
              <span>Risk sensitivity</span>
              <input
                type="range"
                min="0.7"
                max="1.3"
                step="0.05"
                value={riskSensitivity}
                onChange={(e) => setRiskSensitivity(parseFloat(e.target.value))}
              />
              <span>{riskSensitivity.toFixed(2)}x</span>
            </div>
            <div className="map-container mt-6 overflow-hidden rounded-2xl border border-emerald-100">
              <MapContainer center={mapCenter} zoom={4} className="h-full w-full">
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapClickHandler />
                <CircleMarker center={mapCenter} radius={8} pathOptions={{ color: "#16a34a" }} />
                {geoJson && (
                  <GeoJSON
                    data={geoJson}
                    style={(feature) => {
                      const rawId = (feature?.id as string) || ""
                      const fips = String(rawId).padStart(5, "0")
                      const risk = riskByFips[fips]
                      const hasRisk = typeof risk === "number"
                      const color = !hasRisk
                        ? "#e2e8f0"
                        : risk >= 0.7
                        ? "#dc2626"
                        : risk >= 0.5
                        ? "#f97316"
                        : risk >= 0.3
                        ? "#facc15"
                        : risk >= 0.15
                        ? "#4ade80"
                        : "#22c55e"
                      return {
                        color: "#e2e8f0",
                        weight: 0.6,
                        fillColor: color,
                        fillOpacity: hasRisk ? 0.6 : 0.2,
                      }
                    }}
                    onEachFeature={(feature, layer) => {
                      const rawId = (feature?.id as string) || ""
                      const fips = String(rawId).padStart(5, "0")
                      const risk = riskByFips[fips]
                      const details = countyDetails[fips]
                      const nameLabel = details?.county
                        ? `${details.county}${details.state_abbr ? `, ${details.state_abbr}` : ""}`
                        : `County ${fips}`
                      const riskLabel =
                        typeof risk === "number" ? `${(risk * 100).toFixed(1)}%` : "No data"
                      layer.bindTooltip(
                        `${nameLabel}<br/>Risk: ${riskLabel}`,
                        { sticky: true }
                      )
                      layer.on("click", () => {
                        const info = countyDetails[fips]
                        if (info) {
                          setSelectedCounty(info)
                          setChatResponse("Click 'Ask Solixa AI' to get guidance.")
                        }
                      })
                    }}
                  />
                )}
                {alertGeoJson && (
                  <GeoJSON
                    data={alertGeoJson}
                    style={() => ({
                      color: "#dc2626",
                      weight: 1,
                      fillColor: "#fecaca",
                      fillOpacity: 0.25,
                    })}
                  />
                )}
                {emergencyAreas.map((area) => {
                  const risk = facilityRiskMap[area.name]
                  const riskLabel =
                    typeof risk === "number" ? `${(risk * 100).toFixed(1)}%` : "Loading..."
                  return (
                    <CircleMarker
                      key={area.name}
                      center={[area.lat, area.lon]}
                      radius={6}
                      pathOptions={{ color: "#16a34a", fillColor: "#22c55e", fillOpacity: 0.9 }}
                    >
                      <Popup>
                        <div className="text-sm text-slate-700">
                          <div className="font-medium text-emerald-700">{area.name}</div>
                          <div className="text-xs uppercase text-emerald-400">{area.type}</div>
                          <div className="mt-1">Live risk: {riskLabel}</div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  )
                })}
              </MapContainer>
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500">
              {riskLegend.map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ background: item.color }} />
                  {item.label}
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">
              {areaSummary}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {alertSummary}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {modelMetrics}
            </div>
          </div>

          <div className="space-y-6">
            <div ref={inverterRef} className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-100">
              <h3 className="text-lg font-semibold text-emerald-700">Inverter Anomaly Upload</h3>
              <p className="text-sm text-slate-500 mt-2">{anomalySummary}</p>
              <div className="mt-4">
                <FileUpload onChange={scoreInverterData} />
              </div>
              <Button variant="outline" className="mt-4" onClick={loadSampleInverterData}>
                Use Sample Inverter Data
              </Button>
              {anomalySamples.length > 0 && (
                <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/40 p-3">
                  <p className="text-xs font-medium text-emerald-700">Sample anomalies</p>
                  <div className="mt-2 space-y-1 text-xs text-slate-600">
                    {anomalySamples.slice(0, 5).map((row, idx) => (
                      <div key={`${row.TIME_STAMP}-${idx}`} className="flex justify-between">
                        <span>{row.TIME_STAMP}</span>
                        <span className="font-medium text-emerald-700">
                          {Number(row.Value).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-100">
              <h3 className="text-lg font-semibold text-emerald-700">County AI Brief</h3>
              <p className="text-sm text-slate-500 mt-2">
                {selectedCounty
                  ? `Selected: ${selectedCounty.county ?? "County"} ${
                      selectedCounty.state_abbr ? `, ${selectedCounty.state_abbr}` : ""
                    }`
                  : "Select a county on the map to generate guidance."}
              </p>
              <div className="mt-4">
                <MorphPanel
                  onSubmit={(message) => {
                    requestCountyChat(message)
                  }}
                  width={520}
                  height={260}
                  className="justify-start"
                />
              </div>
              <div className="mt-4 text-sm text-slate-600 whitespace-pre-line">
                {chatResponse === "Generating guidance..." ? (
                  <TextShimmer className="text-sm">Generating guidance...</TextShimmer>
                ) : (
                  chatResponse
                )}
              </div>
            </div>
            <div ref={alertsRef} className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-100">
              <h3 className="text-lg font-semibold text-emerald-700">Automated Alerting</h3>
              <p className="text-sm text-slate-500 mt-2">
                Trigger a real SMS via Twilio once the risk surpasses thresholds.
              </p>
              <Button className="mt-4" onClick={sendSmsAlert}>
                Send Test Alert
              </Button>
              <p className="text-xs text-emerald-700 mt-2">{smsStatus}</p>
            </div>
          </div>
        </div>

        <div ref={modelRef} className="mt-10 rounded-3xl bg-white p-6 shadow-sm border border-emerald-100">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-emerald-700">Emergency Area Auto-Scoring</h3>
            <div className="flex gap-2">
              <Button variant="outline" onClick={autoScoreEmergencyAreas}>
                Refresh Scores
              </Button>
              <Button
                variant={autoRefresh ? "secondary" : "outline"}
                onClick={() => setAutoRefresh((prev) => !prev)}
              >
                {autoRefresh ? "Auto Refresh On" : "Auto Refresh Off"}
              </Button>
            </div>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {autoRiskRows.length === 0
              ? emergencyAreas.map((area) => (
                  <div
                    key={area.name}
                    className="rounded-2xl border border-emerald-100 p-4 text-sm text-slate-500"
                  >
                    {area.name} · {area.type}
                  </div>
                ))
              : autoRiskRows.map((row) => (
                  <div
                    key={row.name}
                    className="rounded-2xl border border-emerald-100 p-4 text-sm text-slate-600"
                  >
                    <div className="font-medium text-emerald-700">{row.name}</div>
                    <div className="text-xs uppercase tracking-wide text-emerald-400">
                      {row.type}
                    </div>
                    <div className="mt-2 text-sm">
                      Risk: {row.risk ? `${(row.risk * 100).toFixed(1)}%` : "Unavailable"}
                    </div>
                  </div>
                ))}
          </div>
        </div>

        <div className="mt-10 rounded-3xl bg-white p-6 shadow-sm border border-emerald-100">
          <h3 className="text-lg font-semibold text-emerald-700">Model Validation</h3>
          <p className="text-sm text-slate-500 mt-1">
            ROC, calibration, and stability curves show accuracy and consistency over time.
          </p>
          {evaluationData && (
            <div className="mt-6 grid gap-6 md:grid-cols-3">
              <div className="rounded-2xl border border-emerald-100 p-4">
                <p className="text-sm font-medium text-emerald-700">ROC Curve</p>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart
                    data={(evaluationData.roc_curve?.fpr || []).map((value: number, idx: number) => ({
                      fpr: value,
                      tpr: evaluationData.roc_curve?.tpr?.[idx] ?? 0,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="fpr" />
                    <YAxis />
                    <ChartTooltip />
                    <Line type="monotone" dataKey="tpr" stroke="#16a34a" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-2xl border border-emerald-100 p-4">
                <p className="text-sm font-medium text-emerald-700">Calibration</p>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart
                    data={(evaluationData.calibration?.predicted || []).map(
                      (value: number, idx: number) => ({
                        predicted: value,
                        observed: evaluationData.calibration?.observed?.[idx] ?? 0,
                      })
                    )}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="predicted" />
                    <YAxis />
                    <ChartTooltip />
                    <Line type="monotone" dataKey="observed" stroke="#15803d" dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-2xl border border-emerald-100 p-4">
                <p className="text-sm font-medium text-emerald-700">Yearly Stability</p>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={evaluationData.stability || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="YEAR" />
                    <YAxis />
                    <ChartTooltip />
                    <Line type="monotone" dataKey="mean_pred" stroke="#22c55e" dot={false} />
                    <Line type="monotone" dataKey="mean_actual" stroke="#f97316" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
    </div>
  )
}
