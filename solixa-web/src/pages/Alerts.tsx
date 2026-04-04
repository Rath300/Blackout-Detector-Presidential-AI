import { useState } from "react"
import { Bell, CheckCircle, AlertTriangle, AlertOctagon, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApp, API_BASE } from "@/context/AppContext"

const emergencyAreas = [
  { name: "UCSF Medical Center", type: "hospital", lat: 37.7631, lon: -122.4586 },
  { name: "SF EMS Station 1",    type: "ems",      lat: 37.7946, lon: -122.3999 },
  { name: "Lowell High School",  type: "school",   lat: 37.7325, lon: -122.4856 },
  { name: "SOMA Shelter",        type: "shelter",  lat: 37.7786, lon: -122.4062 },
]

export default function Alerts() {
  const { alertThresholds, setAlertThresholds, alertLog, addAlertLog, energySource, riskSensitivity, anomalyDensity } = useApp()
  const [smsStatus, setSmsStatus] = useState("")
  const [facilityRisks, setFacilityRisks] = useState<Record<string, number>>({})
  const [scanning, setScanning] = useState(false)
  const [customMessage, setCustomMessage] = useState("")

  const sendTestAlert = async () => {
    setSmsStatus("Sending…")
    const msg = customMessage.trim() || "Solixa alert: elevated blackout risk detected. Review backup power and emergency plans."
    const res = await fetch(`${API_BASE}/alerts/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    })
    const data = await res.json()
    const status = res.ok ? `Sent · Twilio: ${data.details?.status ?? "queued"}` : (data.error || "SMS failed.")
    setSmsStatus(status)
    addAlertLog({ time: new Date().toLocaleString(), message: msg, status: res.ok ? "sent" : "failed" })
  }

  const scanFacilities = async () => {
    setScanning(true)
    const m: Record<string, number> = {}
    for (const area of emergencyAreas) {
      const res = await fetch(`${API_BASE}/blackout/risk?lat=${area.lat}&lon=${area.lon}&facilityType=${area.type}&anomalyDensity=${anomalyDensity}&sensitivity=${riskSensitivity}&energySource=${energySource}`)
      const data = await res.json()
      if (res.ok) {
        m[area.name] = data.risk.blackout_risk
        if (data.risk.blackout_risk * 100 >= alertThresholds.high) {
          addAlertLog({ time: new Date().toLocaleTimeString(), message: `HIGH risk at ${area.name}: ${(data.risk.blackout_risk * 100).toFixed(1)}%`, status: "auto-triggered" })
        }
      }
    }
    setFacilityRisks(m)
    setScanning(false)
  }

  const riskIcon = (r: number) => {
    if (r >= 0.7) return <AlertOctagon className="w-4 h-4 text-red-500" />
    if (r >= 0.5) return <AlertTriangle className="w-4 h-4 text-orange-500" />
    if (r >= 0.3) return <AlertTriangle className="w-4 h-4 text-yellow-500" />
    return <CheckCircle className="w-4 h-4 text-green-600" />
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-xl font-bold text-stone-800">Alerts</h1>
        <p className="text-sm text-stone-400">Configure thresholds, scan facilities, and send SMS alerts</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Threshold config */}
        <div className="bg-white rounded-2xl border border-stone-200 p-4">
          <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-3">Alert Thresholds</h3>
          <p className="text-xs text-stone-400 mb-4">Set the risk % at which each level triggers an SMS notification.</p>
          {(["low", "medium", "high"] as const).map(level => (
            <div key={level} className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${level === "high" ? "bg-red-500" : level === "medium" ? "bg-yellow-400" : "bg-green-500"}`} />
                <span className="text-sm text-stone-600 capitalize font-medium">{level} alert</span>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number" min={0} max={100}
                  value={alertThresholds[level]}
                  onChange={e => setAlertThresholds({ ...alertThresholds, [level]: parseInt(e.target.value) || 0 })}
                  className="w-20 h-8 text-sm text-center border-stone-200"
                />
                <span className="text-xs text-stone-400">%</span>
              </div>
            </div>
          ))}
          <div className="mt-4 border-t border-stone-100 pt-4">
            <label className="text-xs text-stone-400 uppercase tracking-widest font-semibold block mb-2">Alert Phone Number</label>
            <Input
              placeholder="+1 (555) 000-0000"
              value={alertThresholds.phoneNumber}
              onChange={e => setAlertThresholds({ ...alertThresholds, phoneNumber: e.target.value })}
              className="border-stone-200 placeholder:text-stone-400 text-sm"
            />
            <p className="text-xs text-stone-400 mt-1.5">Leave blank to use the TWILIO_TO_NUMBER env variable.</p>
          </div>
        </div>

        {/* Send alert */}
        <div className="bg-white rounded-2xl border border-stone-200 p-4 space-y-4">
          <div>
            <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-1">Send Test SMS</h3>
            <p className="text-xs text-stone-400 mb-3">Verify end-to-end Twilio routing with a custom or default message.</p>
            <textarea
              value={customMessage}
              onChange={e => setCustomMessage(e.target.value)}
              placeholder="Custom alert message (optional)…"
              rows={3}
              className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm text-stone-700 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-green-600 resize-none mb-3"
            />
            <Button className="bg-green-700 hover:bg-green-800 text-white" onClick={sendTestAlert}>
              <Bell className="w-4 h-4 mr-2" />Send Test Alert
            </Button>
            {smsStatus && <p className="text-xs text-green-700 mt-2">{smsStatus}</p>}
          </div>

          <div className="pt-3 border-t border-stone-100">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold">SF Critical Facilities</h3>
              <Button size="sm" variant="outline" className="h-7 text-xs border-stone-200 text-stone-500 hover:text-green-700" onClick={scanFacilities} disabled={scanning}>
                {scanning ? "Scanning…" : "Scan Now"}
              </Button>
            </div>
            <div className="space-y-2">
              {emergencyAreas.map(area => {
                const risk = facilityRisks[area.name]
                return (
                  <div key={area.name} className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2">
                      {risk !== undefined ? riskIcon(risk) : <div className="w-4 h-4 rounded-full border-2 border-stone-200" />}
                      <div>
                        <div className="text-xs font-medium text-stone-700">{area.name}</div>
                        <div className="text-[10px] text-stone-400 uppercase">{area.type}</div>
                      </div>
                    </div>
                    {risk !== undefined ? (
                      <span className={`text-xs font-bold tabular-nums ${risk >= 0.20 ? "text-red-600" : risk >= 0.10 ? "text-orange-500" : risk >= 0.05 ? "text-yellow-600" : "text-green-700"}`}>
                        {(risk * 100).toFixed(1)}%
                      </span>
                    ) : <span className="text-xs text-stone-300">—</span>}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Alert log */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold">Alert Log</h3>
        </div>
        {alertLog.length === 0 ? (
          <p className="text-xs text-stone-400">No alerts triggered yet.</p>
        ) : (
          <div className="space-y-2">
            {alertLog.map((entry, i) => (
              <div key={i} className={`flex items-start justify-between px-3 py-2 rounded-lg text-xs ${entry.status === "failed" ? "bg-red-50 border border-red-100" : entry.status === "auto-triggered" ? "bg-amber-50 border border-amber-100" : "bg-green-50 border border-green-100"}`}>
                <div>
                  <div className="font-medium text-stone-700">{entry.message}</div>
                  <div className="text-stone-400 mt-0.5">{entry.time}</div>
                </div>
                <span className={`shrink-0 ml-2 font-semibold uppercase ${entry.status === "failed" ? "text-red-600" : entry.status === "auto-triggered" ? "text-amber-600" : "text-green-700"}`}>
                  {entry.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
