"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { AlertCircle, BarChart3, Home, Shield, Activity, FileText, BarChart } from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarProps {
  open: boolean
}

export default function Sidebar({ open }: SidebarProps) {
  const pathname = usePathname()

  const navItems = [
    { href: "/", label: "Dashboard", icon: Home },
    { href: "/alerts", label: "Alerts", icon: AlertCircle },
    { href: "/realtime", label: "Real-time", icon: Activity },
    { href: "/analysis", label: "Analysis", icon: FileText },
    { href: "/summary", label: "Summary", icon: BarChart },
  ]

  return (
    <aside
      className={cn(
        "fixed md:static inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-sidebar-border transition-transform duration-300 transform",
        open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
      )}
    >
      <div className="p-6 border-b border-sidebar-border flex items-center gap-2">
        <Shield className="h-6 w-6 text-sidebar-primary" />
        <span className="text-lg font-bold text-sidebar-foreground">IDS</span>
      </div>

      <nav className="p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-2 rounded-lg transition-colors",
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent",
              )}
            >
              <Icon className="h-5 w-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
