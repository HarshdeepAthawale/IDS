"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import Layout from "@/components/layout"
import AlertsOverview from "@/components/alerts-overview"
import TrafficStatsOverview from "@/components/traffic-stats-overview"
import InsiderThreatsOverview from "@/components/insider-threats-overview"
import SystemMonitor from "@/components/system-monitor"
import PerformanceMonitor from "@/components/performance-monitor"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"
import { config } from "@/lib/config"
import { flaskApi } from "@/lib/flask-api"

interface DashboardStats {
  totalAlerts: number
  criticalAlerts: number
  activeConnections: number
  totalPackets: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalAlerts: 0,
    criticalAlerts: 0,
    activeConnections: 0,
    totalPackets: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected' | 'unknown'>('unknown')
  const [realTimeConnected, setRealTimeConnected] = useState(false)

  const fetchStats = useCallback(async () => {
    try {
      setError(null)
      const response = await flaskApi.getTrafficStats()
      const data = {
        totalAlerts: response.summary.total_anomalies || 0,
        criticalAlerts: 0, // Would need separate API call
        activeConnections: response.current_stats?.active_connections || 0,
        totalPackets: response.current_stats?.total_packets || 0,
      }
      setStats(data)
      setBackendStatus('connected')
    } catch (err) {
      console.error('Error fetching dashboard stats:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch real-time data'
      setError(errorMessage.includes('Network error') ? 
        'Backend server is not running. Please start the Flask backend server.' : 
        'Failed to fetch real-time data, showing cached data')
      setBackendStatus('disconnected')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    
    // Note: Real-time updates would need to be implemented with Socket.IO
    // For now, we'll rely on polling with optimized intervals
    
    // Set up polling as fallback if enabled - increased interval for better performance
    let interval: NodeJS.Timeout | null = null
    if (config.features.polling) {
      interval = setInterval(fetchStats, Math.max(config.polling.dashboard, 20000)) // Min 20 seconds
    }
    
    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [fetchStats])

  // Memoize expensive computations
  const formattedPacketCount = useMemo(() => {
    return (stats.totalPackets / 1000000).toFixed(1)
  }, [stats.totalPackets])

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground mt-2">Real-time network intrusion detection system</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge 
              variant={backendStatus === 'connected' ? 'default' : 'destructive'}
              className="text-xs"
            >
              {backendStatus === 'connected' ? 'Backend Connected' : 'Backend Disconnected'}
            </Badge>
            <Badge 
              variant={realTimeConnected ? 'default' : 'secondary'}
              className="text-xs flex items-center gap-1"
            >
              {realTimeConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {realTimeConnected ? 'Real-time' : 'Polling'}
            </Badge>
            {loading && (
              <Badge variant="secondary" className="text-xs">
                Loading...
              </Badge>
            )}
          </div>
        </div>
        
        {error && (
          <div className={`border rounded-md p-4 ${
            error.includes('Backend server is not running') 
              ? 'bg-red-50 border-red-200' 
              : 'bg-yellow-50 border-yellow-200'
          }`}>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {error.includes('Backend server is not running') ? (
                  <WifiOff className="h-5 w-5 text-red-400" />
                ) : (
                  <Wifi className="h-5 w-5 text-yellow-400" />
                )}
              </div>
              <div className="ml-3">
                <p className={`text-sm font-medium ${
                  error.includes('Backend server is not running') 
                    ? 'text-red-800' 
                    : 'text-yellow-800'
                }`}>
                  {error.includes('Backend server is not running') ? 'Backend Connection Error' : 'Connection Warning'}
                </p>
                <p className={`text-sm mt-1 ${
                  error.includes('Backend server is not running') 
                    ? 'text-red-700' 
                    : 'text-yellow-700'
                }`}>
                  {error}
                </p>
                {error.includes('Backend server is not running') && (
                  <div className="mt-3">
                    <p className="text-sm text-red-700 font-medium">To fix this:</p>
                    <ol className="text-sm text-red-700 mt-1 list-decimal list-inside space-y-1">
                      <li>Open a terminal/command prompt</li>
                      <li>Navigate to the backend directory</li>
                      <li>Run: <code className="bg-red-100 px-1 rounded">python app.py</code></li>
                      <li>Wait for "Flask IDS Backend started" message</li>
                      <li>Refresh this page</li>
                    </ol>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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
              <div className="text-2xl font-bold text-foreground">{formattedPacketCount}M</div>
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
        
        {/* System Monitor */}
        <SystemMonitor />
      </div>
      
      {/* Performance Monitor */}
      <PerformanceMonitor />
    </Layout>
  )
}
