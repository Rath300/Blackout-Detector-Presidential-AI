import React, { createContext, useContext, useState, useCallback } from "react"

export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1"

export type CountyRisk = {
  fips: string
  risk: number
  county?: string
  state_abbr?: string
  state_name?: string
  nri_risk?: number
  dominant_source?: string
  total_mw?: number
  fossil_pct?: number
}

export type RiskHistoryEntry = {
  id: number
  timestamp: string
  location: string
  energySource: string
  risk: number
  breakdown: Record<string, number>
}

export type AlertThreshold = {
  low: number
  medium: number
  high: number
  phoneNumber: string
}

export type ComparedCounty = CountyRisk & {
  weatherRisk?: number
  mlRisk?: number
  sviScore?: number
}

interface AppState {
  // Location
  mapCenter: [number, number]
  setMapCenter: (c: [number, number]) => void
  selectedLocation: string
  setSelectedLocation: (l: string) => void

  // Energy source
  energySource: string
  setEnergySource: (s: string) => void

  // Risk sensitivity
  riskSensitivity: number
  setRiskSensitivity: (v: number) => void

  // Anomaly
  anomalyDensity: number
  setAnomalyDensity: (v: number) => void

  // Current risk result
  localRisk: number | null
  setLocalRisk: (v: number | null) => void
  riskBreakdown: Record<string, number>
  setRiskBreakdown: (v: Record<string, number>) => void
  weatherData: Record<string, any>
  setWeatherData: (v: Record<string, any>) => void

  // County details
  selectedCounty: CountyRisk | null
  setSelectedCounty: (c: CountyRisk | null) => void
  riskByFips: Record<string, number>
  setRiskByFips: (v: Record<string, number>) => void
  countyDetails: Record<string, CountyRisk>
  setCountyDetails: (v: Record<string, CountyRisk>) => void

  // Risk history
  riskHistory: RiskHistoryEntry[]
  addRiskHistory: (entry: Omit<RiskHistoryEntry, "id">) => void
  clearRiskHistory: () => void

  // Compared counties
  comparedCounties: ComparedCounty[]
  addComparedCounty: (c: ComparedCounty) => void
  removeComparedCounty: (fips: string) => void
  clearComparedCounties: () => void

  // Alert thresholds
  alertThresholds: AlertThreshold
  setAlertThresholds: (v: AlertThreshold) => void

  // Alert log
  alertLog: { time: string; message: string; status: string }[]
  addAlertLog: (entry: { time: string; message: string; status: string }) => void

  // Forecast timeline (for Monitor page)
  forecastTimeline: { hour: string; risk: number; wind: number; precip: number; temp: number }[]
  setForecastTimeline: (v: { hour: string; risk: number; wind: number; precip: number; temp: number }[]) => void
}

const AppContext = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [mapCenter, setMapCenter] = useState<[number, number]>([37.7749, -122.4194])
  const [selectedLocation, setSelectedLocation] = useState("San Francisco, CA")
  const [energySource, setEnergySource] = useState("grid")
  const [riskSensitivity, setRiskSensitivity] = useState(1.0)
  const [anomalyDensity, setAnomalyDensity] = useState(0)
  const [localRisk, setLocalRisk] = useState<number | null>(null)
  const [riskBreakdown, setRiskBreakdown] = useState<Record<string, number>>({})
  const [weatherData, setWeatherData] = useState<Record<string, any>>({})
  const [selectedCounty, setSelectedCounty] = useState<CountyRisk | null>(null)
  const [riskByFips, setRiskByFips] = useState<Record<string, number>>({})
  const [countyDetails, setCountyDetails] = useState<Record<string, CountyRisk>>({})
  const [riskHistory, setRiskHistory] = useState<RiskHistoryEntry[]>([])
  const [comparedCounties, setComparedCounties] = useState<ComparedCounty[]>([])
  const [alertThresholds, setAlertThresholds] = useState<AlertThreshold>({ low: 20, medium: 40, high: 60, phoneNumber: "" })
  const [alertLog, setAlertLog] = useState<{ time: string; message: string; status: string }[]>([])
  const [forecastTimeline, setForecastTimeline] = useState<{ hour: string; risk: number; wind: number; precip: number; temp: number }[]>([])

  let historyId = React.useRef(0)

  const addRiskHistory = useCallback((entry: Omit<RiskHistoryEntry, "id">) => {
    historyId.current += 1
    setRiskHistory(prev => [{ ...entry, id: historyId.current }, ...prev].slice(0, 50))
  }, [])

  const clearRiskHistory = useCallback(() => setRiskHistory([]), [])

  const addComparedCounty = useCallback((c: ComparedCounty) => {
    setComparedCounties(prev => {
      if (prev.find(x => x.fips === c.fips)) return prev
      return [...prev, c].slice(0, 6)
    })
  }, [])

  const removeComparedCounty = useCallback((fips: string) => {
    setComparedCounties(prev => prev.filter(c => c.fips !== fips))
  }, [])

  const clearComparedCounties = useCallback(() => setComparedCounties([]), [])

  const addAlertLog = useCallback((entry: { time: string; message: string; status: string }) => {
    setAlertLog(prev => [entry, ...prev].slice(0, 30))
  }, [])

  return (
    <AppContext.Provider value={{
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
      riskHistory, addRiskHistory, clearRiskHistory,
      comparedCounties, addComparedCounty, removeComparedCounty, clearComparedCounties,
      alertThresholds, setAlertThresholds,
      alertLog, addAlertLog,
      forecastTimeline, setForecastTimeline,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error("useApp must be used within AppProvider")
  return ctx
}

// ── Shared helpers ─────────────────────────────────────────────────────────────

export const ENERGY_SOURCES = [
  { id: "solar",  label: "Solar PV",     hint: "Cloud cover & irradiance drive risk" },
  { id: "wind",   label: "Wind",         hint: "Extreme wind forces turbine shutdown" },
  { id: "hydro",  label: "Hydro",        hint: "Drought & flood levels affect output" },
  { id: "fossil", label: "Fossil Fuel",  hint: "Heat waves spike demand & supply stress" },
  { id: "gas",    label: "Natural Gas",  hint: "Temperature extremes raise demand risk" },
  { id: "grid",   label: "Grid",         hint: "All-source transmission & distribution" },
]

export function riskTextColor(r: number) {
  if (r >= 0.7) return "text-red-600"
  if (r >= 0.5) return "text-orange-500"
  if (r >= 0.3) return "text-yellow-600"
  return "text-green-700"
}

export function riskBgColor(r: number) {
  if (r >= 0.7) return "bg-red-500"
  if (r >= 0.5) return "bg-orange-400"
  if (r >= 0.3) return "bg-yellow-400"
  return "bg-green-600"
}

export function riskBadgeClass(r: number) {
  if (r >= 0.20) return "bg-red-50 text-red-600 border-red-200"
  if (r >= 0.10) return "bg-orange-50 text-orange-600 border-orange-200"
  if (r >= 0.05) return "bg-yellow-50 text-yellow-700 border-yellow-200"
  return "bg-green-50 text-green-700 border-green-200"
}

export function riskLabel(r: number) {
  if (r >= 0.20) return "HIGH"
  if (r >= 0.10) return "ELEVATED"
  if (r >= 0.05) return "MODERATE"
  return "LOW"
}
