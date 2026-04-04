import { useEffect, useState } from "react"
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip as ChartTooltip, ResponsiveContainer } from "recharts"
import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { FileUpload } from "@/components/ui/file-upload"
import { useApp, API_BASE } from "@/context/AppContext"

export default function Model() {
  const { anomalyDensity, setAnomalyDensity } = useApp()
  const [metrics, setMetrics]     = useState<any>(null)
  const [evaluation, setEval]     = useState<any>(null)
  const [anomalySamples, setAnomalySamples] = useState<{ TIME_STAMP: string; Value: number; anomaly_score?: number }[]>([])
  const [anomalySummary, setAnomalySummary] = useState("")

  useEffect(() => {
    fetch(`${API_BASE}/model/metrics`).then(r => r.json()).then(d => { if (d.metrics) setMetrics(d.metrics) }).catch(() => {})
    fetch(`${API_BASE}/model/evaluation`).then(r => r.json()).then(d => { if (d.evaluation) setEval(d.evaluation) }).catch(() => {})
  }, [])

  const scoreInverterData = async (files: File[]) => {
    const file = files[0]; if (!file) return
    const formData = new FormData(); formData.append("file", file)
    const res = await fetch(`${API_BASE}/anomalies/score`, { method: "POST", body: formData })
    const data = await res.json()
    if (!res.ok) { setAnomalySummary(data.error || "Could not score asset data."); return }
    setAnomalyDensity(data.anomaly_density)
    setAnomalySummary(`${data.rows} rows · ${data.anomaly_count} anomalies · ${(data.anomaly_density * 100).toFixed(2)}% anomaly density`)
    setAnomalySamples(data.sample_anomalies || [])
  }

  const loadSampleData = async () => {
    const res = await fetch(`${API_BASE}/anomalies/sample`, { method: "POST" })
    const data = await res.json()
    if (!res.ok) { setAnomalySummary(data.error || "Could not load sample."); return }
    setAnomalyDensity(data.anomaly_density)
    setAnomalySummary(`Sample: ${data.rows} rows · ${data.anomaly_count} anomalies · ${(data.anomaly_density * 100).toFixed(2)}% density`)
    setAnomalySamples(data.sample_anomalies || [])
  }

  const exportMetricsCSV = () => {
    if (!metrics) return
    const rows = [
      ["Metric", "Value"],
      ["AUC", (metrics.auc * 100).toFixed(2) + "%"],
      ["Accuracy", (metrics.accuracy * 100).toFixed(2) + "%"],
      ["Train rows", metrics.train_rows],
      ["Test rows", metrics.test_rows],
    ]
    const csv = rows.map(r => r.join(",")).join("\n")
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url; a.download = "solixa-model-metrics.csv"
    a.click(); URL.revokeObjectURL(url)
  }

  const exportModelReport = () => {
    const lines = [
      "Solixa Model Validation Report",
      `Generated: ${new Date().toLocaleString()}`,
      "",
      "── Model Info ──",
      "Algorithm: Gradient Boosting Classifier",
      "Training data: NOAA Storm Events + CDC SVI",
      "Target: POWER_OUTAGE_LIKELY (binary)",
      "",
      "── Performance Metrics ──",
      metrics ? `AUC: ${(metrics.auc * 100).toFixed(2)}%` : "AUC: N/A",
      metrics ? `Accuracy: ${(metrics.accuracy * 100).toFixed(2)}%` : "Accuracy: N/A",
      metrics ? `Train rows: ${metrics.train_rows}` : "",
      metrics ? `Test rows: ${metrics.test_rows}` : "",
      "",
      "── Asset Anomaly ──",
      anomalySummary || "No asset data loaded.",
      "",
      "── Interpretation ──",
      "AUC > 0.8 indicates strong discrimination between outage/non-outage events.",
      "Calibration curve should follow y=x diagonal for well-calibrated probabilities.",
      "Stability chart shows consistency of predictions across historical years.",
    ]
    const blob = new Blob([lines.join("\n")], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url; a.download = "solixa-model-report.txt"
    a.click(); URL.revokeObjectURL(url)
  }

  const charts = evaluation ? [
    {
      title: "ROC Curve",
      desc: "True positive rate vs false positive rate. Closer to top-left = better.",
      data: (evaluation.roc_curve?.fpr || []).map((v: number, i: number) => ({ fpr: v, tpr: evaluation.roc_curve?.tpr?.[i] ?? 0 })),
      xKey: "fpr", lines: [{ key: "tpr", color: "#15803d", label: "TPR" }],
    },
    {
      title: "Calibration",
      desc: "Predicted vs observed probability. Ideal = diagonal.",
      data: (evaluation.calibration?.predicted || []).map((v: number, i: number) => ({ pred: v, obs: evaluation.calibration?.observed?.[i] ?? 0 })),
      xKey: "pred", lines: [{ key: "obs", color: "#16a34a", label: "Observed" }],
    },
    {
      title: "Yearly Stability",
      desc: "Mean predicted vs actual risk per year.",
      data: evaluation.stability || [],
      xKey: "YEAR", lines: [{ key: "mean_pred", color: "#16a34a", label: "Predicted" }, { key: "mean_actual", color: "#f97316", label: "Actual" }],
    },
  ] : []

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-stone-800">Model Validation</h1>
          <p className="text-sm text-stone-400">Gradient Boosting · NOAA Storm Events + CDC SVI · Isolation Forest anomaly detection</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={exportMetricsCSV} disabled={!metrics} className="border-stone-200 text-stone-500 hover:text-green-700 flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5" />CSV
          </Button>
          <Button size="sm" variant="outline" onClick={exportModelReport} className="border-stone-200 text-stone-500 hover:text-green-700 flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5" />Report
          </Button>
        </div>
      </div>

      {/* Metric cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "AUC", value: `${(metrics.auc * 100).toFixed(1)}%`, note: "Discrimination ability" },
            { label: "Accuracy", value: `${(metrics.accuracy * 100).toFixed(1)}%`, note: "Overall correctness" },
            { label: "Train rows", value: metrics.train_rows?.toLocaleString() ?? "—", note: "Events used for training" },
            { label: "Test rows", value: metrics.test_rows?.toLocaleString() ?? "—", note: "Events used for evaluation" },
          ].map(({ label, value, note }) => (
            <div key={label} className="bg-white rounded-xl border border-stone-200 p-3">
              <div className="text-xs uppercase tracking-widest text-stone-400 mb-1">{label}</div>
              <div className="text-2xl font-bold text-stone-800">{value}</div>
              <div className="text-xs text-stone-400 mt-0.5">{note}</div>
            </div>
          ))}
        </div>
      )}

      {/* Validation charts */}
      {charts.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-3">
          {charts.map(({ title, desc, data, xKey, lines }) => (
            <div key={title} className="bg-white rounded-2xl border border-stone-200 p-4">
              <div className="mb-1">
                <h3 className="text-sm font-semibold text-stone-700">{title}</h3>
                <p className="text-xs text-stone-400">{desc}</p>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={data} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey={xKey} tick={{ fontSize: 9, fill: "#94a3b8" }} />
                  <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} />
                  <ChartTooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", fontSize: 11 }} />
                  {lines.map(l => (
                    <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color} dot={false} strokeWidth={1.8} name={l.label} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-stone-200 p-6 text-center">
          <p className="text-stone-400 text-sm">Validation charts load after the model initialises.</p>
          <p className="text-stone-300 text-xs mt-1">Run <code className="bg-stone-100 px-1 py-0.5 rounded text-stone-500">python -m core.ml.train_risk_model</code> if not trained yet.</p>
        </div>
      )}

      {/* Model info */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <h3 className="text-sm font-semibold text-stone-700 mb-3">Model Architecture</h3>
        <div className="grid gap-3 md:grid-cols-3 text-xs">
          {[
            { label: "Blackout Risk", algo: "Gradient Boosting Classifier", data: "NOAA Storm Events + CDC SVI", purpose: "County-level outage probability" },
            { label: "Asset Anomaly", algo: "Isolation Forest", data: "Inverter / turbine / generator telemetry", purpose: "Detects unusual power output patterns" },
            { label: "Weather Risk", algo: "Heuristic weighting", data: "Open-Meteo API + NWS alerts", purpose: "Per-source weather severity score" },
          ].map(({ label, algo, data, purpose }) => (
            <div key={label} className="rounded-xl border border-stone-100 p-3">
              <div className="font-semibold text-stone-700 mb-1">{label}</div>
              <div className="text-stone-500 mb-0.5"><span className="text-stone-400">Algorithm: </span>{algo}</div>
              <div className="text-stone-500 mb-0.5"><span className="text-stone-400">Data: </span>{data}</div>
              <div className="text-stone-500"><span className="text-stone-400">Purpose: </span>{purpose}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Asset upload */}
      <div className="bg-white rounded-2xl border border-stone-200 p-4">
        <h3 className="text-xs uppercase tracking-widest text-stone-400 font-semibold mb-1">Energy Asset Upload</h3>
        <p className="text-xs text-stone-400 mb-3">Upload telemetry CSV to run Isolation Forest anomaly detection. Results feed into the risk score on the Dashboard.</p>
        <FileUpload onChange={scoreInverterData} />
        <Button variant="outline" size="sm" className="mt-3 text-xs border-stone-200 text-stone-500 hover:text-green-700" onClick={loadSampleData}>
          Use Sample Asset Data
        </Button>
        {anomalySummary && <p className="text-xs text-stone-600 mt-2">{anomalySummary}</p>}
        {anomalySamples.length > 0 && (
          <div className="mt-3 rounded-xl border border-green-100 bg-green-50 p-3">
            <div className="text-xs font-semibold text-stone-600 mb-2">Sample anomaly timestamps</div>
            {anomalySamples.slice(0, 6).map((row, i) => (
              <div key={i} className="flex justify-between text-xs py-0.5">
                <span className="text-stone-400">{row.TIME_STAMP}</span>
                <span className="font-medium text-green-700">{Number(row.Value).toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
