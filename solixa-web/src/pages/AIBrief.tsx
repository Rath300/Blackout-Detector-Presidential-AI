import { useRef, useEffect, useState } from "react"
import { Send, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { useApp, API_BASE, riskTextColor } from "@/context/AppContext"

type Message = { role: "user" | "assistant"; text: string; timestamp: string }

const SUGGESTED_PROMPTS = [
  "What are the top 3 risks for this county?",
  "Create a 72-hour emergency response plan",
  "Which critical facilities need backup power?",
  "What would a grid failure mean for this area?",
  "Estimate recovery time after a blackout event",
  "How does this county compare to state average?",
]

export default function AIBrief() {
  const { selectedCounty, selectedLocation, localRisk, energySource, weatherData } = useApp()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState("")
  const [loading, setLoading]   = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest message
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, loading])

  // Build the context payload — works with or without a county click
  const buildPayload = (prompt: string) => {
    const county = selectedCounty?.county ?? selectedLocation ?? "Current Location"
    const state  = selectedCounty?.state_abbr ?? selectedCounty?.state_name ?? ""
    return {
      county: {
        fips:            selectedCounty?.fips ?? "unknown",
        county,
        state,
        risk:            selectedCounty?.risk ?? localRisk ?? 0,
        energy_source:   energySource,
        weather_summary: weatherData,
        prompt,
      },
    }
  }

  const sendMessage = async (text: string) => {
    const msg = text.trim()
    if (!msg || loading) return

    setMessages(prev => [...prev, { role: "user", text: msg, timestamp: new Date().toLocaleTimeString() }])
    setInput("")
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/chat/county`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload(msg)),
      })
      const data = await res.json()
      const reply = res.ok ? (data.response || "No response received.") : (data.error || "Chat request failed.")
      setMessages(prev => [...prev, { role: "assistant", text: reply, timestamp: new Date().toLocaleTimeString() }])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", text: "Connection error — make sure the backend is running on port 8000.", timestamp: new Date().toLocaleTimeString() }])
    } finally {
      setLoading(false)
    }
  }

  const exportChat = () => {
    const loc = selectedCounty ? `${selectedCounty.county ?? "County"}${selectedCounty.state_abbr ? `, ${selectedCounty.state_abbr}` : ""}` : selectedLocation ?? "Location"
    const lines = [
      `Solixa AI Brief — ${loc}`,
      `Generated: ${new Date().toLocaleString()}`,
      `Energy Source: ${energySource}`,
      `Risk Score: ${localRisk !== null ? `${(localRisk * 100).toFixed(1)}%` : "N/A"}`,
      `Weather: Wind ${weatherData.max_wind ?? "—"} m/s · Precip ${weatherData.total_precip_72h ?? "—"} mm`,
      "", "─── Conversation ───", "",
      ...messages.map(m => `[${m.timestamp}] ${m.role === "user" ? "You" : "Solixa AI"}:\n${m.text}\n`),
    ]
    const blob = new Blob([lines.join("\n")], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url; a.download = `solixa-brief-${loc.replace(/[, ]+/g, "-")}.txt`
    a.click(); URL.revokeObjectURL(url)
  }

  const displayName = selectedCounty
    ? `${selectedCounty.county ?? "County"}${selectedCounty.state_abbr ? `, ${selectedCounty.state_abbr}` : ""}`
    : (selectedLocation ?? "Current Location")

  return (
    <div className="p-4 h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-stone-800">AI Brief</h1>
          <p className="text-sm text-stone-400">Location-specific guidance · {displayName}</p>
        </div>
        {messages.length > 0 && (
          <Button size="sm" variant="outline" onClick={exportChat} className="border-stone-200 text-stone-500 hover:text-green-700 flex items-center gap-2">
            <Download className="w-3.5 h-3.5" />Export
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-[280px_1fr]">
        {/* Left panel */}
        <div className="space-y-3">
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <div className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-2">Analysis Context</div>
            <div className="font-semibold text-stone-800">{displayName}</div>
            {localRisk !== null && (
              <div className={`text-2xl font-bold mt-1 ${riskTextColor(localRisk)}`}>{(localRisk * 100).toFixed(1)}% risk</div>
            )}
            <div className="text-xs text-stone-400 mt-1">{energySource} source{selectedCounty?.fips ? ` · FIPS ${selectedCounty.fips}` : ""}</div>
            {!selectedCounty && (
              <p className="text-xs text-amber-600 mt-2 bg-amber-50 rounded-lg p-2 border border-amber-100">
                Tip: click a county on the Dashboard map for county-specific data.
              </p>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <div className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-3">Suggested Prompts</div>
            <div className="space-y-1.5">
              {SUGGESTED_PROMPTS.map(p => (
                <button key={p} onClick={() => sendMessage(p)} disabled={loading}
                  className="w-full text-left text-xs px-3 py-2 rounded-lg border border-stone-100 text-stone-600 hover:border-green-300 hover:bg-green-50 hover:text-green-700 transition-all disabled:opacity-40">
                  {p}
                </button>
              ))}
            </div>
          </div>

          {Object.keys(weatherData).length > 0 && (
            <div className="bg-white rounded-2xl border border-stone-200 p-4">
              <div className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-2">Current Conditions</div>
              <div className="space-y-1 text-xs">
                {[["Wind", `${weatherData.max_wind ?? "—"} m/s`], ["Precip", `${weatherData.total_precip_72h ?? "—"} mm`], ["Cloud", `${weatherData.avg_cloud_pct ?? "—"}%`], ["Temp", `${weatherData.min_temp_c ?? "—"}–${weatherData.max_temp_c ?? "—"}°C`], ["NWS alerts", `${weatherData.active_alerts ?? 0}`]].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-stone-400">{k}</span>
                    <span className="font-medium text-stone-700">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Chat panel */}
        <div className="flex flex-col bg-white rounded-2xl border border-stone-200 overflow-hidden" style={{ minHeight: 500 }}>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="w-12 h-12 rounded-full bg-green-50 border border-green-200 flex items-center justify-center mb-3">
                  <Send className="w-5 h-5 text-green-600" />
                </div>
                <p className="text-stone-500 text-sm font-medium">Ask Solixa AI</p>
                <p className="text-stone-400 text-xs mt-1">Use a suggested prompt or type your own question.</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${msg.role === "user" ? "bg-green-700 text-white rounded-br-sm" : "bg-stone-100 text-stone-700 rounded-bl-sm"}`}>
                    <div className="whitespace-pre-line leading-relaxed">{msg.text}</div>
                    <div className={`text-[10px] mt-1.5 ${msg.role === "user" ? "text-green-200" : "text-stone-400"}`}>{msg.timestamp}</div>
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-stone-100 rounded-2xl rounded-bl-sm px-4 py-3">
                  <TextShimmer className="text-sm">Generating guidance…</TextShimmer>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-stone-100 p-3">
            <form onSubmit={e => { e.preventDefault(); sendMessage(input) }} className="flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder={`Ask about ${displayName}…`}
                disabled={loading}
                className="flex-1 rounded-xl border border-stone-200 px-3 py-2 text-sm text-stone-700 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-transparent disabled:bg-stone-50"
              />
              <Button type="submit" size="sm" disabled={!input.trim() || loading} className="bg-green-700 hover:bg-green-800 text-white px-4">
                <Send className="w-3.5 h-3.5" />
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
