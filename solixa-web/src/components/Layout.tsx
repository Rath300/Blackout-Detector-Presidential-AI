import { NavLink, Outlet } from "react-router-dom"
import { LayoutDashboard, Activity, GitCompare, Bell, Bot, BarChart2 } from "lucide-react"
import { useApp, riskLabel, riskBadgeClass } from "@/context/AppContext"

const NAV = [
  { to: "/",        icon: LayoutDashboard, label: "Dashboard",  desc: "Map & risk score" },
  { to: "/monitor", icon: Activity,        label: "Monitor",    desc: "72h timeline & history" },
  { to: "/compare", icon: GitCompare,      label: "Compare",    desc: "Multi-county compare" },
  { to: "/alerts",  icon: Bell,            label: "Alerts",     desc: "Thresholds & SMS" },
  { to: "/ai",      icon: Bot,             label: "AI Brief",   desc: "County guidance" },
  { to: "/model",   icon: BarChart2,       label: "Model",      desc: "Validation & export" },
]

export default function Layout() {
  const { localRisk, selectedLocation, energySource } = useApp()

  return (
    <div className="flex min-h-screen bg-white text-stone-800">

      {/* ── Sidebar ── */}
      <aside className="hidden md:flex flex-col w-56 shrink-0 border-r border-stone-200 bg-white sticky top-0 h-screen">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-stone-100">
          <span className="text-lg font-bold tracking-widest text-green-800">SOLIXA</span>
          <p className="text-[10px] text-stone-400 mt-0.5 leading-tight">Energy Grid Risk Intelligence</p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label, desc }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                  isActive
                    ? "bg-green-50 text-green-800 font-semibold"
                    : "text-stone-500 hover:bg-stone-50 hover:text-stone-800"
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <div>
                <div className="leading-tight">{label}</div>
                <div className="text-[10px] text-stone-400 font-normal leading-tight">{desc}</div>
              </div>
            </NavLink>
          ))}
        </nav>

        {/* Status footer */}
        <div className="px-4 py-3 border-t border-stone-100 space-y-1.5">
          <div className="text-[10px] uppercase tracking-widest text-stone-400 font-semibold">Active Context</div>
          <div className="text-xs text-stone-600 truncate">{selectedLocation}</div>
          <div className="text-xs text-stone-400">{energySource} source</div>
          {localRisk !== null && (
            <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full border ${riskBadgeClass(localRisk)}`}>
              <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${localRisk >= 0.7 ? "bg-red-500" : localRisk >= 0.5 ? "bg-orange-500" : localRisk >= 0.3 ? "bg-yellow-500" : "bg-green-600"}`} />
              {riskLabel(localRisk)} · {(localRisk * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </aside>

      {/* ── Mobile top bar ── */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-stone-200 px-4 py-2.5 flex items-center justify-between">
        <span className="text-base font-bold tracking-widest text-green-800">SOLIXA</span>
        <div className="flex gap-1">
          {NAV.map(({ to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `p-2 rounded-lg ${isActive ? "bg-green-50 text-green-700" : "text-stone-400"}`
              }
            >
              <Icon className="w-4 h-4" />
            </NavLink>
          ))}
        </div>
      </div>

      {/* ── Main content ── */}
      <main className="flex-1 min-w-0 md:pt-0 pt-14">
        <Outlet />
      </main>
    </div>
  )
}
