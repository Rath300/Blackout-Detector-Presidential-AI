import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMapEvents, useMap } from "react-leaflet"
import * as L from "leaflet"
import type { GeoJsonObject } from "geojson"
import "leaflet/dist/leaflet.css"
import { Sun, Wind, Droplets, Flame, Zap, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { FileUpload } from "@/components/ui/file-upload"
import {
  useApp, API_BASE, riskTextColor, riskBgColor, riskLabel, ENERGY_SOURCES,
  type CountyRisk,
} from "@/context/AppContext"

// ── Constants ──────────────────────────────────────────────────────────────────
const COUNTY_GEOJSON_URL =
  "https://cdn.jsdelivr.net/gh/plotly/datasets@master/geojson-counties-fips.json"

const SOURCE_ICONS: Record<string, React.ElementType> = {
  solar: Sun, wind: Wind, hydro: Droplets, fossil: Flame, gas: Flame, grid: Zap,
}

const EMERGENCY_AREAS = [
  { name: "UCSF Medical Center", type: "hospital", lat: 37.7631, lon: -122.4586 },
  { name: "SF EMS Station 1",    type: "ems",       lat: 37.7946, lon: -122.3999 },
  { name: "Lowell High School",  type: "school",    lat: 37.7325, lon: -122.4856 },
  { name: "SOMA Shelter",        type: "shelter",   lat: 37.7786, lon: -122.4062 },
]

const RISK_LEGEND = [
  { label: "< 15%  Low",       color: "#22c55e" },
  { label: "15–20%  Moderate", color: "#facc15" },
  { label: "20–25%  Elevated", color: "#f97316" },
  { label: "25%+  High",       color: "#dc2626" },
]

// ── MapClickHandler ────────────────────────────────────────────────────────────
function MapClickHandler({ onMapClick }: { onMapClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) { onMapClick(e.latlng.lat, e.latlng.lng) },
  })
  return null
}

// ── FlyToLocation — syncs mapCenter state → actual Leaflet view ────────────────
function FlyToLocation({ center }: { center: [number, number] }) {
  const map = useMap()
  useEffect(() => {
    map.flyTo(center, map.getZoom(), { animate: true, duration: 1.0 })
  }, [center[0], center[1]])
  return null
}

// ── Colour helpers ─────────────────────────────────────────────────────────────
function countyFillColor(risk: number | undefined) {
  if (risk === undefined) return "#e2e8f0"
  if (risk >= 0.25) return "#dc2626"   // HIGH  (>25%)
  if (risk >= 0.20) return "#f97316"   // ELEVATED (20–25%)
  if (risk >= 0.15) return "#facc15"   // MODERATE (15–20%)
  return "#22c55e"                     // LOW/MINIMAL (<15%) — green
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate()
  const {
    mapCenter, setMapCenter,
    selectedLocation, setSelectedLocation,
    energySource, setEnergySource,
    riskSensitivity, setRiskSensitivity,
    anomalyDensity, setAnomalyDensity,
    localRisk, setLocalRisk,
    riskBreakdown, setRiskBreakdown,
    weatherData, setWeatherData,
    selectedCounty, setSelectedCounty,
    riskByFips, setRiskByFips,
    countyDetails, setCountyDetails,
    addRiskHistory,
    setForecastTimeline,
    addComparedCounty,
    alertThresholds, addAlertLog,
  } = useApp()

  const [searchQuery, setSearchQuery]   = useState("")
  const [searchStatus, setSearchStatus] = useState("")
  const [stateCode, setStateCode]       = useState("")
  const [geoJson, setGeoJson]           = useState<GeoJsonObject | null>(null)
  const [geoJsonKey, setGeoJsonKey]     = useState("empty")   // forces re-mount when risk data loads
  const [mapStatus, setMapStatus]       = useState<string>("")
  const [checkingRisk, setCheckingRisk] = useState(false)
  const [alertSummary, setAlertSummary] = useState("")
  const [alertGeoJson, setAlertGeoJson] = useState<GeoJsonObject | null>(null)
  const [anomalySummary, setAnomalySummary] = useState("")
  const [anomalySamples, setAnomalySamples] = useState<{ TIME_STAMP: string; Value: number }[]>([])
  const [facilityRiskMap, setFacilityRiskMap] = useState<Record<string, number>>({})
  const [modelMetrics, setModelMetrics] = useState("")
  const [countyNri, setCountyNri] = useState<Record<string, any>>({})
  const [countyGen, setCountyGen] = useState<Record<string, any>>({})

  const geoJsonLoaded = useRef(false)
  const currentSource = ENERGY_SOURCES.find(s => s.id === energySource) ?? ENERGY_SOURCES[5]
  const SourceIcon = SOURCE_ICONS[energySource] ?? Zap

  // ── Load county GeoJSON (once) + risk choropleth ────────────────────────────
  const loadCountyRisk = useCallback(async (state?: string) => {
    setMapStatus("Loading county risk data…")
    try {
      const url = `${API_BASE}/blackout/choropleth${state ? `?state=${encodeURIComponent(state)}` : ""}`
      const riskRes = await fetch(url)
      if (!riskRes.ok) throw new Error(`Risk API ${riskRes.status}`)
      const riskPayload = await riskRes.json()

      const nextRisk: Record<string, number> = {}
      const nextDetails: Record<string, CountyRisk> = {}
      ;(riskPayload.counties ?? []).forEach((row: any) => {
        const fips = String(row.fips ?? "").padStart(5, "0")
        nextRisk[fips] = parseFloat(row.risk) || 0
        nextDetails[fips] = { fips, risk: nextRisk[fips], county: row.county, state_abbr: row.state_abbr, state_name: row.state_name }
      })
      setRiskByFips(nextRisk)
      setCountyDetails(nextDetails)
      setMapStatus(`${Object.keys(nextRisk).length} counties loaded`)

      // Load GeoJSON only once – AFTER risk data is in state so styles apply on first render
      if (!geoJsonLoaded.current) {
        setMapStatus("Loading county boundaries…")
        const geoRes = await fetch(COUNTY_GEOJSON_URL)
        if (!geoRes.ok) throw new Error(`GeoJSON ${geoRes.status}`)
        const geoPayload = await geoRes.json()
        geoJsonLoaded.current = true
        setGeoJson(geoPayload)
        setGeoJsonKey("loaded")   // triggers re-mount so styles from nextRisk apply immediately
        setMapStatus("")
      } else {
        // GeoJSON already loaded – just force style refresh via key change
        setGeoJsonKey(`refresh-${Date.now()}`)
        setMapStatus("")
      }
    } catch (err: any) {
      setMapStatus(`Map error: ${err.message}`)
    }
  }, [API_BASE])

  // ── Initial load ────────────────────────────────────────────────────────────
  useEffect(() => {
    loadCountyRisk()
    fetch(`${API_BASE}/model/metrics`)
      .then(r => r.json())
      .then(d => { if (d.metrics?.auc) setModelMetrics(`AUC ${(d.metrics.auc * 100).toFixed(1)}% · Acc ${(d.metrics.accuracy * 100).toFixed(1)}%`) })
      .catch(() => {})
  }, [])

  // ── Auto-refresh weather + alert summary when location/source changes ───────
  useEffect(() => {
    const [lat, lon] = mapCenter
    const run = async () => {
      try {
        const [riskRes, alertRes] = await Promise.all([
          fetch(`${API_BASE}/blackout/risk?lat=${lat}&lon=${lon}&facilityType=community&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}&energySource=${energySource}`),
          fetch(`${API_BASE}/weather/alerts?lat=${lat}&lon=${lon}`),
        ])
        if (riskRes.ok) {
          const d = await riskRes.json()
          const bd = d.risk?.components ?? {}
          if (Object.keys(weatherData).length === 0) setWeatherData(d.weather_summary ?? {})
          // Populate forecast timeline for Monitor page
          const ws = d.weather_summary ?? {}
          if (!ws.hourly_raw) {
            // Build rough timeline from summary stats for the Monitor page
            const rough = Array.from({ length: 72 }, (_, i) => ({
              hour: `H+${i}`, risk: Math.round((d.risk?.blackout_risk ?? 0) * 100), wind: ws.max_wind ?? 0, precip: 0, temp: ws.max_temp_c ?? 20,
            }))
            setForecastTimeline(rough)
          }
        }
        if (alertRes.ok) {
          const d = await alertRes.json()
          const features = d.features ?? []
          setAlertSummary(features.length ? `${features.length} active NWS alert(s): ${features.slice(0, 2).map((f: any) => f.properties?.event).filter(Boolean).join(", ")}` : "No active NWS alerts.")
          setAlertGeoJson(d)
        }
      } catch (_) {}
    }
    run()
  }, [mapCenter, energySource])

  // ── Geocode search ──────────────────────────────────────────────────────────
  const handleGeocode = async () => {
    if (!searchQuery.trim()) return
    setSearchStatus("Searching…")
    try {
      const res = await fetch(`${API_BASE}/geocode?query=${encodeURIComponent(searchQuery)}`)
      if (!res.ok) { setSearchStatus("Search failed — backend unreachable"); return }
      const data = await res.json()
      const first = data.results?.[0]
      if (first) {
        const lat = parseFloat(first.lat)
        const lon = parseFloat(first.lon)
        setMapCenter([lat, lon])
        setSelectedLocation(first.display_name ?? searchQuery)
        setSearchStatus("")
        setSearchQuery("")
      } else {
        setSearchStatus(`No results for "${searchQuery}"`)
      }
    } catch {
      setSearchStatus("Search error — check connection")
    }
  }

  // ── Map click handler ───────────────────────────────────────────────────────
  const handleMapClick = useCallback((lat: number, lon: number) => {
    setMapCenter([lat, lon])
    setSelectedLocation(`${lat.toFixed(4)}, ${lon.toFixed(4)}`)
  }, [])

  // ── Run risk check ──────────────────────────────────────────────────────────
  const checkRisk = async () => {
    const [lat, lon] = mapCenter
    setCheckingRisk(true)
    try {
      const res = await fetch(`${API_BASE}/blackout/risk?lat=${lat}&lon=${lon}&facilityType=community&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}&energySource=${energySource}`)
      const data = await res.json()
      if (!res.ok) return
      const bd = data.risk?.components ?? {}
      setLocalRisk(data.risk.blackout_risk)
      const breakdown = {
        "Weather":      Math.round((bd.weather_risk ?? 0) * 100),
        "Outage hist.": Math.round((bd.outage_risk ?? 0) * 100),
        "Asset anomaly":Math.round((bd.anomaly_risk ?? 0) * 100),
        "ML model":     Math.round((bd.ml_risk ?? 0) * 100),
      }
      setRiskBreakdown(breakdown)
      setWeatherData(data.weather_summary ?? {})
      if (data.nri_profile) setCountyNri(data.nri_profile)
      if (data.gen_profile) setCountyGen(data.gen_profile)
      addRiskHistory({ timestamp: new Date().toLocaleTimeString(), location: selectedLocation, energySource, risk: data.risk.blackout_risk, breakdown })

      if (data.risk.blackout_risk * 100 >= alertThresholds.high) {
        addAlertLog({ time: new Date().toLocaleTimeString(), message: `HIGH risk ${(data.risk.blackout_risk * 100).toFixed(1)}% at ${selectedLocation}`, status: "auto-triggered" })
      }
    } finally {
      setCheckingRisk(false)
    }
  }

  // ── Anomaly upload ──────────────────────────────────────────────────────────
  const scoreAssetData = async (files: File[]) => {
    const file = files[0]; if (!file) return
    const formData = new FormData(); formData.append("file", file)
    const res = await fetch(`${API_BASE}/anomalies/score`, { method: "POST", body: formData })
    const data = await res.json()
    if (!res.ok) { setAnomalySummary(data.error || "Upload failed."); return }
    setAnomalyDensity(data.anomaly_density)
    setAnomalySummary(`${data.rows} rows · ${data.anomaly_count} anomalies · ${(data.anomaly_density * 100).toFixed(2)}% density`)
    setAnomalySamples(data.sample_anomalies ?? [])
  }

  const loadSampleData = async () => {
    const res = await fetch(`${API_BASE}/anomalies/sample`, { method: "POST" })
    const data = await res.json()
    if (!res.ok) { setAnomalySummary(data.error || "Sample load failed."); return }
    setAnomalyDensity(data.anomaly_density)
    setAnomalySummary(`Sample: ${data.rows} rows · ${data.anomaly_count} anomalies · ${(data.anomaly_density * 100).toFixed(2)}% density`)
    setAnomalySamples(data.sample_anomalies ?? [])
  }

  // ── Facility risk scoring ───────────────────────────────────────────────────
  useEffect(() => {
    const scoreAreas = async () => {
      const m: Record<string, number> = {}
      for (const a of EMERGENCY_AREAS) {
        try {
          const res = await fetch(`${API_BASE}/blackout/risk?lat=${a.lat}&lon=${a.lon}&facilityType=${a.type}&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}&energySource=${energySource}`)
          const d = await res.json()
          if (res.ok) m[a.name] = d.risk.blackout_risk
        } catch (_) {}
      }
      setFacilityRiskMap(m)
    }
    scoreAreas()
  }, [energySource])

  // ── GeoJSON style & per-feature (memoised for performance) ─────────────────
  // Note: these are recreated each time geoJsonKey changes (forced re-mount)
  const geoJsonStyle = useCallback((feature: any) => {
    const fips = String(feature?.id ?? feature?.properties?.GEOID ?? "").padStart(5, "0")
    const risk = riskByFips[fips]
    return {
      color: "#cbd5e1", weight: 0.4,
      fillColor: countyFillColor(risk),
      fillOpacity: risk !== undefined ? 0.65 : 0.1,
    }
  }, [riskByFips])

  const onEachFeature = useCallback((feature: any, layer: L.Layer) => {
    const fips = String(feature?.id ?? feature?.properties?.GEOID ?? "").padStart(5, "0")
    const risk = riskByFips[fips]
    const d = countyDetails[fips]
    const name = d?.county ? `${d.county}${d.state_abbr ? `, ${d.state_abbr}` : ""}` : (feature?.properties?.NAME ?? `FIPS ${fips}`)
    const riskText = risk !== undefined ? `${(risk * 100).toFixed(1)}%` : "No data"

    layer.bindTooltip(`<b>${name}</b><br/>Risk: <b>${riskText}</b>`, { sticky: true, opacity: 0.9 })

    layer.on("click", (e) => {
      L.DomEvent.stopPropagation(e as unknown as Event)
      const county: CountyRisk = d ?? { fips, risk: risk ?? 0, county: feature?.properties?.NAME ?? fips }
      setSelectedCounty(county)
      addComparedCounty({ ...county, risk: risk ?? 0 })

      // Immediately show the choropleth risk so the card updates without waiting for API
      if (risk !== undefined) {
        setLocalRisk(risk)
        setRiskBreakdown({ "ML model": Math.round(risk * 100), "Weather": 0, "Outage hist.": 0, "Asset anomaly": 0 })
      }

      // Extract the county centroid from the Leaflet layer geometry, then run full risk check
      try {
        const center = (layer as L.Polygon).getBounds().getCenter()
        const lat = center.lat
        const lon = center.lng
        setMapCenter([lat, lon])
        setSelectedLocation(name)

        // Full async risk fetch for this county's centroid
        setCheckingRisk(true)
        fetch(`${API_BASE}/blackout/risk?lat=${lat}&lon=${lon}&facilityType=community&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}&energySource=${energySource}`)
          .then(r => r.json())
          .then(data => {
            if (!data.risk) return
            const bd = data.risk.components ?? {}
            setLocalRisk(data.risk.blackout_risk)
            setRiskBreakdown({
              "Weather":       Math.round((bd.weather_risk ?? 0) * 100),
              "Outage hist.":  Math.round((bd.outage_risk ?? 0) * 100),
              "Asset anomaly": Math.round((bd.anomaly_risk ?? 0) * 100),
              "ML model":      Math.round((bd.ml_risk ?? 0) * 100),
              "NRI hazards":   Math.round((bd.nri_bonus ?? 0) * 100),
            })
            setWeatherData(data.weather_summary ?? {})
            if (data.nri_profile) setCountyNri(data.nri_profile)
            if (data.gen_profile) setCountyGen(data.gen_profile)
            addRiskHistory({ timestamp: new Date().toLocaleTimeString(), location: name, energySource, risk: data.risk.blackout_risk, breakdown: {} })
          })
          .catch(() => {})
          .finally(() => setCheckingRisk(false))
      } catch (_) {}
    })
  }, [riskByFips, countyDetails, anomalyDensity, riskSensitivity, energySource])

  return (
    <div className="p-4 space-y-4">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-stone-800">Dashboard</h1>
        <p className="text-sm text-stone-400">Real-time energy grid blackout risk · {selectedLocation}</p>
      </div>

      {/* Energy source selector */}
      <div className="bg-white rounded-2xl border border-stone-200 px-4 py-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs uppercase tracking-widest text-stone-400 font-semibold">Energy Source</span>
          <span className="text-xs text-stone-400">· pre-set for San Francisco</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {ENERGY_SOURCES.map(({ id, label, hint }) => {
            const Icon = SOURCE_ICONS[id] ?? Zap
            return (
              <button key={id} title={hint} onClick={() => setEnergySource(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${energySource === id ? "bg-green-700 text-white border-green-700 shadow-sm" : "bg-white text-stone-500 border-stone-200 hover:border-green-600 hover:text-green-700"}`}>
                <Icon className="w-3.5 h-3.5" />{label}
              </button>
            )
          })}
        </div>
        <p className="mt-1.5 text-xs text-stone-400">{currentSource.hint}</p>
      </div>

      {/* Control bar */}
      <div className="bg-white rounded-xl border border-stone-200 px-4 py-2.5 flex flex-wrap items-center gap-3">
        <div className="flex flex-col gap-0.5">
          <div className="flex gap-1.5">
            <Input value={searchQuery} onChange={e => { setSearchQuery(e.target.value); setSearchStatus("") }} onKeyDown={e => e.key === "Enter" && handleGeocode()} placeholder="Search city or address…" className="max-w-[220px] h-8 text-sm border-stone-200 placeholder:text-stone-400" />
            <Button variant="outline" size="sm" onClick={handleGeocode} className="h-8 border-stone-200 text-stone-600 hover:text-green-700 hover:border-green-600">Search</Button>
          </div>
          {searchStatus && <span className={`text-xs pl-1 ${searchStatus.startsWith("No results") || searchStatus.includes("error") || searchStatus.includes("failed") ? "text-red-500" : "text-stone-400"}`}>{searchStatus}</span>}
        </div>
        <div className="w-px h-4 bg-stone-200" />
        <span className="text-xs text-stone-400">Sensitivity</span>
        <input type="range" min="0.7" max="1.3" step="0.05" value={riskSensitivity} onChange={e => setRiskSensitivity(parseFloat(e.target.value))} className="w-24 accent-green-700" />
        <span className="text-xs text-stone-500 w-8">{riskSensitivity.toFixed(2)}×</span>
        <Button size="sm" className="ml-auto bg-green-700 hover:bg-green-800 text-white flex items-center gap-1.5" onClick={checkRisk} disabled={checkingRisk}>
          {checkingRisk && <Loader2 className="w-3 h-3 animate-spin" />}Run Risk Check
        </Button>
        <span className="text-xs text-stone-400 hidden md:block truncate max-w-[180px]">{selectedLocation}</span>
      </div>

      {/* Main grid */}
      <div className="grid gap-4 md:grid-cols-[1fr_320px]">
        {/* Map */}
        <div className="bg-white rounded-2xl border border-stone-200 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-stone-100">
            <h2 className="font-semibold text-stone-700 text-sm">County Risk Heat Map</h2>
            <div className="flex items-center gap-2">
              {mapStatus && (
                <span className="text-xs text-stone-400 flex items-center gap-1">
                  {mapStatus.startsWith("Map error") ? null : <Loader2 className="w-3 h-3 animate-spin" />}
                  {mapStatus}
                </span>
              )}
              <Input value={stateCode} onChange={e => setStateCode(e.target.value.toUpperCase())} placeholder="State e.g. CA" className="w-24 h-7 text-xs border-stone-200 placeholder:text-stone-400" />
              <Button variant="outline" size="sm" className="h-7 text-xs border-stone-200 text-stone-600" onClick={() => loadCountyRisk(stateCode || undefined)}>Load</Button>
            </div>
          </div>
          <div style={{ height: 460 }}>
            <MapContainer
              center={mapCenter}
              zoom={5}
              style={{ height: "100%", width: "100%" }}
              scrollWheelZoom
            >
              <TileLayer
                attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapClickHandler onMapClick={handleMapClick} />
              <FlyToLocation center={mapCenter} />
              <CircleMarker center={mapCenter} radius={8} pathOptions={{ color: "#15803d", fillColor: "#22c55e", fillOpacity: 0.9, weight: 2 }}>
                <Popup><span className="text-sm font-medium">{selectedLocation}</span></Popup>
              </CircleMarker>

              {geoJson && (
                <GeoJSON
                  key={geoJsonKey}
                  data={geoJson}
                  style={geoJsonStyle}
                  onEachFeature={onEachFeature}
                />
              )}

              {alertGeoJson && (
                <GeoJSON data={alertGeoJson} style={() => ({ color: "#dc2626", weight: 1, fillColor: "#fecaca", fillOpacity: 0.25 })} />
              )}

              {EMERGENCY_AREAS.map((area) => (
                <CircleMarker key={area.name} center={[area.lat, area.lon]} radius={6} pathOptions={{ color: "#15803d", fillColor: "#16a34a", fillOpacity: 0.9, weight: 2 }}>
                  <Popup>
                    <div className="text-sm font-semibold text-green-800">{area.name}</div>
                    <div className="text-xs text-green-600 uppercase mb-1">{area.type}</div>
                    <div className="text-xs text-stone-600">Risk: {facilityRiskMap[area.name] !== undefined ? `${(facilityRiskMap[area.name] * 100).toFixed(1)}%` : "Loading…"}</div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
          <div className="flex flex-wrap items-center gap-3 px-4 py-2 border-t border-stone-100">
            {RISK_LEGEND.map(item => (
              <div key={item.label} className="flex items-center gap-1.5 text-xs text-stone-500">
                <span className="h-2.5 w-2.5 rounded-full inline-block" style={{ background: item.color }} />{item.label}
              </div>
            ))}
            {modelMetrics && <span className="ml-auto text-xs text-stone-400">{modelMetrics}</span>}
          </div>
          {alertSummary && <div className="px-4 pb-2 text-xs text-amber-600">{alertSummary}</div>}
          <div className="px-4 pb-2 text-xs text-stone-400">Click any county to select it · Click map to set analysis point</div>
        </div>

        {/* Right panel */}
        <div className="space-y-3">
          {/* Risk score */}
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase tracking-widest text-stone-400 font-semibold">Local Risk</span>
              <span className="flex items-center gap-1 text-xs text-stone-400"><SourceIcon className="w-3.5 h-3.5 text-green-700" />{currentSource.label}</span>
            </div>
            {localRisk !== null ? (
              <>
                <div className="flex items-end gap-3 mb-2">
                  <span className={`text-5xl font-bold tabular-nums ${riskTextColor(localRisk)}`}>{(localRisk * 100).toFixed(1)}%</span>
                  <span className={`text-sm font-bold mb-1.5 ${riskTextColor(localRisk)}`}>{riskLabel(localRisk)}</span>
                </div>
                <div className="w-full h-1.5 bg-stone-100 rounded-full mb-4">
                  <div className={`h-1.5 rounded-full transition-all duration-700 ${riskBgColor(localRisk)}`} style={{ width: `${(localRisk * 100).toFixed(1)}%` }} />
                </div>
                <div className="space-y-2.5">
                  {Object.entries(riskBreakdown).map(([label, val]) => (
                    <div key={label}>
                      <div className="flex justify-between text-xs mb-0.5">
                        <span className="text-stone-500">{label}</span>
                        <span className="font-medium text-stone-700">{val}%</span>
                      </div>
                      <div className="h-1 bg-stone-100 rounded-full">
                        <div className="h-1 bg-green-600 rounded-full transition-all duration-500" style={{ width: `${Math.min(val, 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <button onClick={() => navigate("/monitor")} className="mt-3 text-xs text-green-700 hover:underline">View 72h timeline →</button>
              </>
            ) : (
              <p className="text-stone-400 text-sm mt-2">Press <span className="text-green-700 font-medium">Run Risk Check</span> to score {selectedLocation}.</p>
            )}
          </div>

          {/* Weather */}
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <span className="text-xs uppercase tracking-widest text-stone-400 font-semibold block mb-3">Weather · {currentSource.label}</span>
            {Object.keys(weatherData).length > 0 ? (
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                {[
                  ["Max wind", `${weatherData.max_wind ?? "—"} m/s`],
                  ["Gust", `${weatherData.max_gust ?? "—"} m/s`],
                  ["Precip 72h", `${weatherData.total_precip_72h ?? "—"} mm`],
                  ["Cloud avg", `${weatherData.avg_cloud_pct ?? "—"}%`],
                  ["Temp range", `${weatherData.min_temp_c ?? "—"}–${weatherData.max_temp_c ?? "—"}°C`],
                  ["NWS alerts", `${weatherData.active_alerts ?? 0}`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-stone-400">{k}</span>
                    <span className="font-medium text-stone-700">{v}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-stone-400">Weather loads automatically. Run a risk check to update.</p>
            )}
          </div>

          {/* Asset upload */}
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-1">Energy Asset Upload</h3>
            <p className="text-xs text-stone-400 mb-3">Upload inverter, turbine, or generator telemetry CSV to factor anomaly density into the risk score.</p>
            <FileUpload onChange={scoreAssetData} />
            <Button variant="outline" size="sm" className="mt-3 w-full text-xs border-stone-200 text-stone-500 hover:text-green-700" onClick={loadSampleData}>
              Use Sample Asset Data
            </Button>
            {anomalySamples.length > 0 && (
              <div className="mt-3 rounded-xl border border-green-100 bg-green-50 p-2.5">
                <p className="text-xs font-medium text-green-700 mb-1.5">{anomalySummary}</p>
                {anomalySamples.slice(0, 4).map((row, i) => (
                  <div key={i} className="flex justify-between text-xs">
                    <span className="text-stone-400 truncate max-w-[120px]">{String(row.TIME_STAMP)}</span>
                    <span className="font-medium text-green-700">{Number(row.Value).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
            {!anomalySamples.length && anomalySummary && <p className="text-xs text-stone-400 mt-2">{anomalySummary}</p>}
          </div>

          {/* Selected county — enriched with NRI + EIA data */}
          {selectedCounty && (
            <div className="bg-white rounded-2xl border border-green-200 p-4 space-y-3">
              <div>
                <div className="text-xs uppercase tracking-widest text-green-700 font-semibold mb-0.5">County Selected</div>
                <div className="text-sm font-semibold text-stone-800">{selectedCounty.county}{selectedCounty.state_abbr ? `, ${selectedCounty.state_abbr}` : ""}</div>
                <div className={`text-2xl font-bold mt-0.5 ${riskTextColor(localRisk ?? selectedCounty.risk)}`}>
                  {((localRisk ?? selectedCounty.risk) * 100).toFixed(1)}%
                  <span className="text-xs font-normal text-stone-400 ml-1">blackout risk</span>
                </div>
              </div>

              {/* NRI hazard scores */}
              {countyNri.hazards && Object.keys(countyNri.hazards).length > 0 && (
                <div>
                  <div className="text-xs text-stone-400 uppercase tracking-widest font-semibold mb-1.5">FEMA Hazard Exposure</div>
                  <div className="space-y-1">
                    {Object.entries(countyNri.hazards as Record<string, number>)
                      .filter(([, v]) => v > 0.05)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 5)
                      .map(([label, val]) => (
                        <div key={label}>
                          <div className="flex justify-between text-xs mb-0.5">
                            <span className="text-stone-500">{label}</span>
                            <span className="font-medium text-stone-700">{(val * 100).toFixed(0)}th pct</span>
                          </div>
                          <div className="h-1 bg-stone-100 rounded-full">
                            <div className={`h-1 rounded-full ${val > 0.7 ? "bg-red-500" : val > 0.4 ? "bg-orange-400" : "bg-yellow-400"}`}
                              style={{ width: `${Math.min(val * 100, 100)}%` }} />
                          </div>
                        </div>
                      ))}
                  </div>
                  {countyNri.risk_rating && (
                    <div className="text-xs text-stone-400 mt-1">NRI rating: <span className="font-medium text-stone-600">{countyNri.risk_rating}</span></div>
                  )}
                </div>
              )}

              {/* Generation mix */}
              {countyGen.total_mw > 0 && (
                <div>
                  <div className="text-xs text-stone-400 uppercase tracking-widest font-semibold mb-1.5">Grid Generation Mix</div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    {[
                      ["Total capacity", `${countyGen.total_mw?.toLocaleString()} MW`],
                      ["Generators", `${countyGen.n_generators}`],
                      ["Fossil %", `${(countyGen.fossil_pct * 100).toFixed(0)}%`],
                      ["Renewable %", `${(countyGen.renewable_pct * 100).toFixed(0)}%`],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-stone-400">{k}</span>
                        <span className="font-medium text-stone-700">{v}</span>
                      </div>
                    ))}
                  </div>
                  {/* Fuel bar */}
                  <div className="mt-2 h-2.5 w-full rounded-full overflow-hidden flex">
                    <div className="bg-orange-400 h-full" style={{ width: `${(countyGen.fossil_pct * 100).toFixed(0)}%` }} title="Fossil" />
                    <div className="bg-sky-400 h-full" style={{ width: `${Math.min((countyGen.solar_mw / countyGen.total_mw) * 100, 100).toFixed(0)}%` }} title="Solar" />
                    <div className="bg-green-400 h-full" style={{ width: `${Math.min((countyGen.wind_mw / countyGen.total_mw) * 100, 100).toFixed(0)}%` }} title="Wind" />
                    <div className="bg-blue-400 h-full" style={{ width: `${Math.min((countyGen.hydro_mw / countyGen.total_mw) * 100, 100).toFixed(0)}%` }} title="Hydro" />
                    <div className="bg-purple-400 h-full" style={{ width: `${Math.min((countyGen.nuclear_mw / countyGen.total_mw) * 100, 100).toFixed(0)}%` }} title="Nuclear" />
                    <div className="bg-stone-200 flex-1" title="Other" />
                  </div>
                  <div className="flex gap-2 mt-1 flex-wrap">
                    {[["bg-orange-400","Fossil"],["bg-sky-400","Solar"],["bg-green-400","Wind"],["bg-blue-400","Hydro"],["bg-purple-400","Nuclear"]].map(([c,l]) => (
                      <span key={l} className="flex items-center gap-1 text-[10px] text-stone-400"><span className={`w-2 h-2 rounded-full ${c}`}/>{l}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <Button size="sm" className="text-xs bg-green-700 hover:bg-green-800 text-white flex-1" onClick={() => navigate("/ai")}>Ask AI</Button>
                <Button size="sm" variant="outline" className="text-xs border-green-300 text-green-700 flex-1" onClick={() => navigate("/compare")}>Compare</Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SF facilities row */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <div className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-3">SF Critical Facilities</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {EMERGENCY_AREAS.map(area => {
            const risk = facilityRiskMap[area.name]
            return (
              <div key={area.name} className="flex flex-col">
                <span className="text-xs font-medium text-stone-700">{area.name}</span>
                <span className="text-xs text-stone-400 uppercase mt-0.5">{area.type}</span>
                {risk !== undefined
                  ? <span className={`text-base font-bold mt-1 ${riskTextColor(risk)}`}>{(risk * 100).toFixed(1)}%</span>
                  : <span className="text-sm text-stone-300 mt-1">Loading…</span>}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
