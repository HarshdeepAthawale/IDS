"use client"

import { useState, useEffect } from "react"
import Layout from "@/components/layout"
import AlertsOverview from "@/components/alerts-overview"
import TrafficStatsOverview from "@/components/traffic-stats-overview"
import InsiderThreatsOverview from "@/components/insider-threats-overview"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalAlerts: 0,
    criticalAlerts: 0,
    activeConnections: 0,
    totalPackets: 0,
  })

  useEffect(() => {
    // Simulate fetching dashboard stats
    const mockStats = {
      totalAlerts: 1247,
      criticalAlerts: 23,
      activeConnections: 156,
      totalPackets: 2847392,
    }
    setStats(mockStats)
  }, [])

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-2">Real-time network intrusion detection system</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">{stats.totalAlerts}</div>
              <p className="text-xs text-muted-foreground mt-1">Last 24 hours</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-destructive">Critical Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">{stats.criticalAlerts}</div>
              <p className="text-xs text-muted-foreground mt-1">Requires attention</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Active Connections</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">{stats.activeConnections}</div>
              <p className="text-xs text-muted-foreground mt-1">Currently monitored</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Packets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">{(stats.totalPackets / 1000000).toFixed(1)}M</div>
              <p className="text-xs text-muted-foreground mt-1">Analyzed</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <AlertsOverview />
          </div>
          <div>
            <InsiderThreatsOverview />
          </div>
        </div>

        {/* Traffic Stats */}
        <TrafficStatsOverview />
      </div>
    </Layout>
  )
}
