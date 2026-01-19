import React, { useState } from "react"
import { Home, MapPin, AlertTriangle, Upload, Settings } from "lucide-react"

interface NavItemProps {
  icon: React.ElementType
  isActive?: boolean
  onClick?: () => void
  indicatorPosition: number
  position: number
}

const NavItem: React.FC<NavItemProps> = ({
  icon: Icon,
  isActive = false,
  onClick,
  indicatorPosition,
  position,
}) => {
  const distance = Math.abs(indicatorPosition - position)
  const spotlightOpacity = isActive ? 1 : Math.max(0, 1 - distance * 0.6)

  return (
    <button
      className="relative flex items-center justify-center w-12 h-12 mx-1 transition-all duration-400"
      onClick={onClick}
    >
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-24 bg-gradient-to-b from-emerald-200/60 to-transparent blur-lg rounded-full transition-opacity duration-400"
        style={{
          opacity: spotlightOpacity,
          transitionDelay: isActive ? "0.1s" : "0s",
        }}
      />
      <Icon
        className={`w-6 h-6 transition-colors duration-200 ${
          isActive ? "text-emerald-700" : "text-emerald-300 hover:text-emerald-500"
        }`}
        strokeWidth={isActive ? 2.5 : 2}
      />
    </button>
  )
}

export const SpotlightNav = () => {
  const [activeIndex, setActiveIndex] = useState(0)

  const navItems = [
    { icon: Home, label: "Overview" },
    { icon: MapPin, label: "Risk Map" },
    { icon: Upload, label: "Inverter Upload" },
    { icon: AlertTriangle, label: "Alerts" },
    { icon: Settings, label: "Settings" },
  ]

  return (
    <nav className="relative flex items-center px-2 py-3 bg-white/80 backdrop-blur-sm rounded-full shadow-sm border border-emerald-100">
      <div
        className="absolute top-0 h-[2px] bg-emerald-500 transition-all duration-400 ease-in-out"
        style={{
          left: `${activeIndex * 56 + 18}px`,
          width: "40px",
          transform: "translateY(-1px)",
        }}
      />
      {navItems.map((item, index) => (
        <NavItem
          key={item.label}
          icon={item.icon}
          isActive={activeIndex === index}
          onClick={() => setActiveIndex(index)}
          indicatorPosition={activeIndex}
          position={index}
        />
      ))}
    </nav>
  )
}
