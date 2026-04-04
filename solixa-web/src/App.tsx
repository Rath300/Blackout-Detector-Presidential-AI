import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AppProvider } from "@/context/AppContext"
import Layout from "@/components/Layout"
import Dashboard from "@/pages/Dashboard"
import Monitor from "@/pages/Monitor"
import Compare from "@/pages/Compare"
import Alerts from "@/pages/Alerts"
import AIBrief from "@/pages/AIBrief"
import Model from "@/pages/Model"

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="monitor" element={<Monitor />} />
            <Route path="compare" element={<Compare />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="ai" element={<AIBrief />} />
            <Route path="model" element={<Model />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  )
}
