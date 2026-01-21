"use client"

import { useState, useEffect, useCallback, useMemo, Suspense, startTransition } from "react"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Wifi, WifiOff } from "lucide-react"
import { useWebSocket } from "@/hooks/use-websocket"
import { useDebounce } from "@/hooks/use-debounce"
import { flaskApi } from "@/lib/flask-api"
import dynamic from "next/dynamic"

// Lazy load heavy components
const AlertsOverview = dynamic(() => import("@/components/alerts-overview"), { ssr: false })
const TrafficStatsOverview = dynamic(() => import("@/components/traffic-stats-overview"), { ssr: false })
const InsiderThreatsOverview = dynamic(() => import("@/components/insider-threats-overview"), { ssr: false })
const PerformanceMonitor = dynamic(() => import("@/components/performance-monitor"), { ssr: false })

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
  const [httpApiConnected, setHttpApiConnected] = useState(false)
  
  // Real-time WebSocket connection (shared with all components)
  const { isConnected: realTimeConnected, isConnecting, error: wsError, on, off } = useWebSocket({ room: 'dashboard' })

  const fetchStats = useCallback(async () => {
    try {
      // Use realtime stats endpoint for faster initial load
      let realtimeData
      try {
        const response = await fetch('/api/stats/realtime')
        if (response.ok) {
          realtimeData = await response.json()
        }
      } catch {
        // Fallback to regular stats if realtime endpoint fails
      }
      
      // Fallback to regular traffic stats if realtime doesn't have all data
      const [trafficResponse, criticalResponse] = await Promise.all([
        flaskApi.getTrafficStats(),
        flaskApi.getCriticalAlerts().catch(() => ({ unresolved_count: 0 }))
      ])
      
      const data = {
        totalAlerts: realtimeData?.summary?.total_anomalies || trafficResponse.summary.total_anomalies || 0,
        criticalAlerts: criticalResponse.unresolved_count || 0,
        activeConnections: realtimeData?.current_stats?.active_connections || trafficResponse.current_stats?.active_connections || 0,
        totalPackets: realtimeData?.current_stats?.total_packets || trafficResponse.current_stats?.total_packets || 0,
      }
      setStats(data)
      setHttpApiConnected(true)
      // Clear error if HTTP API succeeds
      setError(null)
    } catch (err) {
      console.error('Error fetching dashboard stats:', err)
      setHttpApiConnected(false)
      // Don't set error here - let the combined status logic handle it
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  // Combined backend status based on both HTTP API and WebSocket
  useEffect(() => {
    // If either HTTP API or WebSocket is connected, backend is connected
    if (realTimeConnected || httpApiConnected) {
      setBackendStatus('connected')
      setError(null)
    } else if (isConnecting) {
      // Still connecting, don't show error yet
      setBackendStatus('unknown')
      setError(null)
    } else {
      // Both are disconnected and not connecting
      setBackendStatus('disconnected')
      const errorMessage = wsError ? 
        'Backend server is not running. Please start the Flask backend server.' :
        'Failed to connect to backend. Please start the Flask backend server.'
      setError(errorMessage)
    }
  }, [realTimeConnected, httpApiConnected, isConnecting, wsError])

  // Debounced state for WebSocket updates
  const [pendingStatsUpdate, setPendingStatsUpdate] = useState<Partial<DashboardStats> | null>(null)
  const debouncedPendingUpdate = useDebounce(pendingStatsUpdate, 100)

  // Apply debounced updates (only when values actually change, using transitions for smooth updates)
  useEffect(() => {
    if (debouncedPendingUpdate) {
      startTransition(() => {
        setStats(prev => {
          // Only update if values actually changed
          const hasChanges = Object.keys(debouncedPendingUpdate).some(
            key => prev[key as keyof DashboardStats] !== debouncedPendingUpdate[key as keyof DashboardStats]
          )
          if (!hasChanges) return prev // Return same reference if no changes
          return { ...prev, ...debouncedPendingUpdate }
        })
      })
      setPendingStatsUpdate(null)
    }
  }, [debouncedPendingUpdate])

  // Real-time WebSocket updates for dashboard stats (with debouncing)
  useEffect(() => {
    if (!realTimeConnected) {
      // Only use polling as true fallback when WebSocket is disconnected
      const fallbackInterval = setInterval(() => {
        fetchStats()
      }, 5000)
      return () => clearInterval(fallbackInterval)
    }

    const handleTrafficUpdate = (data: any) => {
      const trafficData = data.data || data
      setPendingStatsUpdate(prev => ({
        ...prev,
        activeConnections: trafficData.active_connections,
        totalPackets: trafficData.total_packets,
      }))
    }

    const handleNewAlert = (data: any) => {
      setStats(prev => ({
        ...prev,
        totalAlerts: prev.totalAlerts + 1,
      }))
    }

    on('traffic_update', handleTrafficUpdate)
    on('new_alert', handleNewAlert)

    return () => {
      off('traffic_update', handleTrafficUpdate)
      off('new_alert', handleNewAlert)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [realTimeConnected]) // on/off are stable from context

  // Memoize expensive computations
  const formattedPacketCount = useMemo(() => {
    return (stats.totalPackets / 1000000).toFixed(1)
  }, [stats.totalPackets])

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-2">Real-time network intrusion detection system</p>
        </div>
        
        {backendStatus === 'disconnected' && error && (
          <div className="border rounded-md p-4 bg-destructive/10 border-destructive/20">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <WifiOff className="h-5 w-5 text-destructive" />
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-destructive">
                  Backend Disconnected
                </p>
                <p className="text-sm mt-1 text-destructive/80">
                  {error}
                </p>
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
              <div 
                key={stats.totalAlerts}
                className="text-2xl font-bold text-foreground transition-all duration-200"
              >
                {stats.totalAlerts}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Last 24 hours</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-destructive">Critical Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div 
                key={stats.criticalAlerts}
                className="text-2xl font-bold text-destructive transition-all duration-200"
              >
                {stats.criticalAlerts}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Requires attention</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Active Connections</CardTitle>
            </CardHeader>
            <CardContent>
              <div 
                key={stats.activeConnections}
                className="text-2xl font-bold text-foreground transition-all duration-200"
              >
                {stats.activeConnections}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Currently monitored</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Packets</CardTitle>
            </CardHeader>
            <CardContent>
              <div 
                key={formattedPacketCount}
                className="text-2xl font-bold text-foreground transition-all duration-200"
              >
                {formattedPacketCount}M
              </div>
              <p className="text-xs text-muted-foreground mt-1">Analyzed</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Suspense fallback={<div className="h-96 flex items-center justify-center">Loading alerts...</div>}>
              <AlertsOverview />
            </Suspense>
          </div>
          <div>
            <Suspense fallback={<div className="h-96 flex items-center justify-center">Loading threats...</div>}>
              <InsiderThreatsOverview />
            </Suspense>
          </div>
        </div>

        {/* Traffic Stats */}
        <Suspense fallback={<div className="h-96 flex items-center justify-center">Loading traffic stats...</div>}>
          <TrafficStatsOverview />
        </Suspense>
        
      </div>
      
      {/* Performance Monitor */}
      <Suspense fallback={null}>
        <PerformanceMonitor />
      </Suspense>
    </Layout>
  )
}
