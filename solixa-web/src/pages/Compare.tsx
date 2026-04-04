import { useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer, Legend } from "recharts"
import { X, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApp, API_BASE, riskTextColor, riskBgColor, riskLabel } from "@/context/AppContext"

export default function Compare() {
  const { comparedCounties, addComparedCounty, removeComparedCounty, clearComparedCounties, energySource, riskSensitivity, anomalyDensity, countyDetails } = useApp()
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const searchCounty = async () => {
    if (!searchQuery) return
    const res = await fetch(`${API_BASE}/geocode?query=${encodeURIComponent(searchQuery)}`)
    if (!res.ok) return
    const data = await res.json()
    setSearchResults(data.results?.slice(0, 4) ?? [])
  }

  const addCountyFromResult = async (result: any) => {
    setLoading(true)
    setSearchResults([])
    setSearchQuery("")
    try {
      const lat = parseFloat(result.lat)
      const lon = parseFloat(result.lon)

      // Use backend FIPS lookup (avoids CORS issue with geo.fcc.gov from browser)
      const [riskRes, fipsRes] = await Promise.all([
        fetch(`${API_BASE}/blackout/risk?lat=${lat}&lon=${lon}&facilityType=community&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}&energySource=${energySource}`),
        fetch(`${API_BASE}/fips-lookup?lat=${lat}&lon=${lon}`),
      ])
      const data = await riskRes.json()
      if (!riskRes.ok) return

      let fips = `custom-${Date.now()}`
      let county = result.display_name.split(",")[0].trim()
      let stateAbbr = result.display_name.split(",")[1]?.trim() ?? ""

      if (fipsRes.ok) {
        const fipsData = await fipsRes.json()
        fips = fipsData.fips ?? fips
        county = fipsData.county?.county ?? county
        stateAbbr = fipsData.county?.state_abbr ?? stateAbbr
      }

      addComparedCounty({
        fips: String(fips).padStart(5, "0"),
        county,
        state_abbr: stateAbbr,
        risk: data.risk.blackout_risk,
        weatherRisk: data.risk.components?.weather_risk,
        mlRisk: data.risk.components?.ml_risk,
        sviScore: data.svi_score,
      })
    } finally {
      setLoading(false)
    }
  }

  // Add from already-loaded county details
  const addFromMap = () => {
    Object.values(countyDetails).slice(0, 4).forEach(c => {
      if (comparedCounties.length < 6) addComparedCounty({ ...c, risk: c.risk })
    })
  }

  const chartData = comparedCounties.map(c => ({
    name: c.county ? `${c.county}${c.state_abbr ? `, ${c.state_abbr}` : ""}` : c.fips,
    "Overall Risk": Math.round(c.risk * 100),
    "Weather": Math.round((c.weatherRisk ?? 0) * 100),
    "ML Model": Math.round((c.mlRisk ?? 0) * 100),
    "SVI": Math.round((c.sviScore ?? 0) * 100),
  }))

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-stone-800">County Comparison</h1>
          <p className="text-sm text-stone-400">Compare up to 6 counties side by side · {energySource} source</p>
        </div>
        {comparedCounties.length > 0 && (
          <Button size="sm" variant="outline" className="border-stone-200 text-stone-500 hover:text-red-600" onClick={clearComparedCounties}>
            Clear All
          </Button>
        )}
      </div>

      {/* Search to add county */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-3">Add County</h3>
        <div className="flex gap-2 mb-3">
          <Input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && searchCounty()} placeholder="Search for a county or city…" className="border-stone-200 placeholder:text-stone-400" />
          <Button variant="outline" size="sm" onClick={searchCounty} className="border-stone-200 text-stone-600 hover:text-green-700 shrink-0">Search</Button>
          {Object.keys(countyDetails).length > 0 && (
            <Button size="sm" variant="outline" onClick={addFromMap} className="border-stone-200 text-stone-600 hover:text-green-700 shrink-0 flex items-center gap-1">
              <Plus className="w-3 h-3" />From Map
            </Button>
          )}
        </div>
        {searchResults.length > 0 && (
          <div className="space-y-1">
            {searchResults.map((r, i) => (
              <button key={i} onClick={() => addCountyFromResult(r)}
                className="w-full text-left px-3 py-2 text-sm rounded-lg border border-stone-100 hover:border-green-300 hover:bg-green-50 text-stone-600 transition-all">
                {r.display_name}
              </button>
            ))}
          </div>
        )}
        {loading && <p className="text-xs text-stone-400 mt-2">Fetching risk data…</p>}
        <p className="text-xs text-stone-400 mt-2">
          Tip: click any county on the Dashboard map to auto-add it here.
        </p>
      </div>

      {comparedCounties.length === 0 ? (
        <div className="bg-white rounded-2xl border border-stone-200 p-10 text-center">
          <p className="text-stone-400 text-sm">No counties added yet.</p>
          <p className="text-stone-300 text-xs mt-1">Search above or click counties on the Dashboard map.</p>
        </div>
      ) : (
        <>
          {/* Bar chart */}
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <h2 className="text-sm font-semibold text-stone-700 mb-3">Risk Comparison Chart</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#94a3b8" }} angle={-25} textAnchor="end" />
                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} unit="%" domain={[0, 100]} />
                <ChartTooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", fontSize: 11 }} formatter={(v: number) => [`${v}%`]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Overall Risk" fill="#15803d" radius={[3, 3, 0, 0]} />
                <Bar dataKey="Weather" fill="#0ea5e9" radius={[3, 3, 0, 0]} />
                <Bar dataKey="ML Model" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                <Bar dataKey="SVI" fill="#f97316" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <div className="bg-white rounded-2xl border border-stone-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-stone-100">
                  <th className="text-left px-4 py-2.5 text-xs uppercase tracking-widest text-stone-400">County</th>
                  <th className="text-right px-4 py-2.5 text-xs uppercase tracking-widest text-stone-400">Overall</th>
                  <th className="text-right px-4 py-2.5 text-xs uppercase tracking-widest text-stone-400 hidden sm:table-cell">Weather</th>
                  <th className="text-right px-4 py-2.5 text-xs uppercase tracking-widest text-stone-400 hidden sm:table-cell">ML Model</th>
                  <th className="text-right px-4 py-2.5 text-xs uppercase tracking-widest text-stone-400 hidden sm:table-cell">SVI</th>
                  <th className="text-right px-4 py-2.5 text-xs uppercase tracking-widest text-stone-400">Level</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {comparedCounties.map(c => (
                  <tr key={c.fips} className="border-b border-stone-50 last:border-0 hover:bg-stone-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-stone-700">
                      {c.county ?? c.fips}{c.state_abbr ? `, ${c.state_abbr}` : ""}
                    </td>
                    <td className={`px-4 py-3 text-right font-bold tabular-nums ${riskTextColor(c.risk)}`}>
                      {(c.risk * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right text-stone-500 hidden sm:table-cell">
                      {c.weatherRisk !== undefined ? `${(c.weatherRisk * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-stone-500 hidden sm:table-cell">
                      {c.mlRisk !== undefined ? `${(c.mlRisk * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-stone-500 hidden sm:table-cell">
                      {c.sviScore !== undefined ? `${(c.sviScore * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full border ${c.risk >= 0.20 ? "bg-red-50 text-red-600 border-red-200" : c.risk >= 0.10 ? "bg-orange-50 text-orange-600 border-orange-200" : c.risk >= 0.05 ? "bg-yellow-50 text-yellow-700 border-yellow-200" : "bg-green-50 text-green-700 border-green-200"}`}>
                        {riskLabel(c.risk)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => removeComparedCounty(c.fips)} className="text-stone-300 hover:text-red-500 transition-colors">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
