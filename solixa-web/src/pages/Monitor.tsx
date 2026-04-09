import { useEffect, useState } from "react"
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip as ChartTooltip, ResponsiveContainer, AreaChart, Area, Legend } from "recharts"
import { Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useApp, API_BASE, riskTextColor, riskLabel, riskBadgeClass } from "@/context/AppContext"

export default function Monitor() {
  const { mapCenter, energySource, riskSensitivity, anomalyDensity, selectedLocation, riskHistory, clearRiskHistory, forecastTimeline, setForecastTimeline, localRisk } = useApp()
  const [loading, setLoading] = useState(false)
  const [hourlyForecast, setHourlyForecast] = useState<any[]>([])

  const loadForecast = async () => {
    setLoading(true)
    const [lat, lon] = mapCenter
    try {
      const res = await fetch(`${API_BASE}/weather/forecast?lat=${lat}&lon=${lon}&hours=72`)
      const data = await res.json()
      if (!res.ok) return

      const hourly = data.forecast?.hourly ?? {}
      const times  = hourly.time ?? []
      const winds  = hourly.wind_speed_10m ?? []
      const gusts  = hourly.wind_gusts_10m ?? []
      const precip = hourly.precipitation ?? []
      const temps  = hourly.temperature_2m ?? []
      const clouds = hourly.cloudcover ?? []

      // Build a naive per-hour estimated risk
      const SOURCE_WIND_W: Record<string, number> = { solar: 0.10, wind: 0.65, hydro: 0.10, fossil: 0.10, gas: 0.10, grid: 0.30 }
      const SOURCE_PRECIP_W: Record<string, number> = { solar: 0.15, wind: 0.10, hydro: 0.45, fossil: 0.05, gas: 0.05, grid: 0.20 }
      const SOURCE_CLOUD_W: Record<string, number> = { solar: 0.55, wind: 0.00, hydro: 0.00, fossil: 0.00, gas: 0.00, grid: 0.10 }
      const SOURCE_TEMP_W: Record<string, number> = { solar: 0.10, wind: 0.15, hydro: 0.30, fossil: 0.65, gas: 0.65, grid: 0.25 }

      const ww = SOURCE_WIND_W[energySource] ?? 0.30
      const pw = SOURCE_PRECIP_W[energySource] ?? 0.20
      const cw = SOURCE_CLOUD_W[energySource] ?? 0.10
      const tw = SOURCE_TEMP_W[energySource] ?? 0.20

      const points = times.slice(0, 72).map((t: string, i: number) => {
        const wind  = winds[i]  ?? 0
        const gust  = gusts[i]  ?? 0
        const prec  = precip[i] ?? 0
        const temp  = temps[i]  ?? 20
        const cloud = clouds[i] ?? 0

        // Mirror backend calibration: 0 below threshold, 1.0 at severe event
        const windScore   = Math.min(Math.max(Math.max(wind - 20, 0) / 60, Math.max(gust - 25, 0) / 55), 1)
        const precipScore = Math.min(Math.max(prec - 5, 0) / 45, 1)
        const cloudScore  = cloud / 100
        const heatRisk    = Math.max(0, (temp - 35) / 15)
        const freezeRisk  = Math.max(0, (-5 - temp) / 20)
        const tempScore   = Math.min(Math.max(heatRisk, freezeRisk), 1)

        const raw = ww * windScore + pw * precipScore + cw * cloudScore + tw * tempScore
        const est = Math.min(raw * 0.45 * riskSensitivity, 1)  // match backend 0.45 damping

        return {
          hour: new Date(t).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", hour12: true }),
          risk: Math.round(est * 100),
          wind: Math.round(wind),
          precip: Math.round(prec * 10) / 10,
          temp: Math.round(temp),
          cloud: Math.round(cloud),
        }
      })
      setHourlyForecast(points)
      setForecastTimeline(points)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadForecast() }, [mapCenter, energySource])

  // Stats
  const maxRisk = hourlyForecast.length ? Math.max(...hourlyForecast.map(h => h.risk)) : null
  const avgRisk = hourlyForecast.length ? Math.round(hourlyForecast.reduce((a, b) => a + b.risk, 0) / hourlyForecast.length) : null
  const peakHour = maxRisk !== null ? hourlyForecast.find(h => h.risk === maxRisk) : null

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-stone-800">Risk Monitor</h1>
          <p className="text-sm text-stone-400">72-hour forecast & session history · {selectedLocation}</p>
        </div>
        <Button size="sm" variant="outline" className="border-stone-200 text-stone-600 hover:text-green-700" onClick={loadForecast} disabled={loading}>
          {loading ? "Loading…" : "Refresh Forecast"}
        </Button>
      </div>

      {/* Stat cards */}
      {hourlyForecast.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Current Risk", value: localRisk !== null ? `${(localRisk * 100).toFixed(1)}%` : "Run check", color: localRisk !== null ? riskTextColor(localRisk) : "text-stone-400" },
            { label: "72h Peak", value: maxRisk !== null ? `${maxRisk}%` : "—", color: maxRisk !== null ? riskTextColor(maxRisk / 100) : "text-stone-400" },
            { label: "72h Average", value: avgRisk !== null ? `${avgRisk}%` : "—", color: "text-stone-700" },
            { label: "Peak at", value: peakHour?.hour ?? "—", color: "text-stone-700" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white rounded-xl border border-stone-200 p-3">
              <div className="text-xs text-stone-400 uppercase tracking-widest mb-1">{label}</div>
              <div className={`text-lg font-bold ${color}`}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* 72-hour risk timeline */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <h2 className="text-sm font-semibold text-stone-700 mb-3">72-Hour Risk Forecast</h2>
        {hourlyForecast.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={hourlyForecast} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#16a34a" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="hour" tick={{ fontSize: 9, fill: "#94a3b8" }} interval={11} />
              <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} domain={[0, 100]} unit="%" />
              <ChartTooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", fontSize: 11 }} formatter={(v: number) => [`${v}%`, "Risk"]} />
              <Area type="monotone" dataKey="risk" stroke="#16a34a" strokeWidth={2} fill="url(#riskGradient)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex items-center justify-center text-stone-400 text-sm">Loading forecast data…</div>
        )}
      </div>

      {/* Weather drivers grid */}
      {hourlyForecast.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <h2 className="text-sm font-semibold text-stone-700 mb-3">Wind Speed (m/s)</h2>
            <ResponsiveContainer width="100%" height={150}>
              <LineChart data={hourlyForecast}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="hour" tick={{ fontSize: 8, fill: "#94a3b8" }} interval={11} />
                <YAxis tick={{ fontSize: 8, fill: "#94a3b8" }} />
                <ChartTooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", fontSize: 11 }} />
                <Line type="monotone" dataKey="wind" stroke="#0ea5e9" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <h2 className="text-sm font-semibold text-stone-700 mb-3">Temperature (°C)</h2>
            <ResponsiveContainer width="100%" height={150}>
              <LineChart data={hourlyForecast}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="hour" tick={{ fontSize: 8, fill: "#94a3b8" }} interval={11} />
                <YAxis tick={{ fontSize: 8, fill: "#94a3b8" }} />
                <ChartTooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", fontSize: 11 }} />
                <Line type="monotone" dataKey="temp" stroke="#f97316" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Risk history log */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-stone-700">Risk Check History</h2>
          {riskHistory.length > 0 && (
            <button onClick={clearRiskHistory} className="flex items-center gap-1 text-xs text-stone-400 hover:text-red-500 transition-colors">
              <Trash2 className="w-3 h-3" />Clear
            </button>
          )}
        </div>
        {riskHistory.length === 0 ? (
          <p className="text-xs text-stone-400">No risk checks yet. Run a risk check from the Dashboard.</p>
        ) : (
          <div className="space-y-2">
            {riskHistory.map(entry => (
              <div key={entry.id} className="flex items-center justify-between py-2 border-b border-stone-50 last:border-0">
                <div>
                  <div className="text-xs font-medium text-stone-700">{entry.location}</div>
                  <div className="text-xs text-stone-400">{entry.timestamp} · {entry.energySource}</div>
                </div>
                <span className={`text-sm font-bold tabular-nums ${riskTextColor(entry.risk)}`}>
                  {(entry.risk * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
