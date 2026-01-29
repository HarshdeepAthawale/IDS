"use client"

import { useState, useEffect, useCallback, useMemo, Suspense, startTransition } from "react"
import Link from "next/link"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff, FileSearch, ExternalLink } from "lucide-react"
import { useWebSocket } from "@/hooks/use-websocket"
import { useDebounce } from "@/hooks/use-debounce"
import { flaskApi } from "@/lib/flask-api"
import dynamic from "next/dynamic"

interface LatestPcapSummary {
  metadata?: { packets_processed?: number; filename?: string }
  risk?: { score?: number; level?: string }
  detections?: unknown[]
}

// Lazy load heavy components
const AlertsOverview = dynamic(() => import("@/components/alerts-overview"), { ssr: false })
const TrafficStatsOverview = dynamic(() => import("@/components/traffic-stats-overview"), { ssr: false })
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

  // Latest PCAP analysis (for dashboard card)
  const [pcapLatest, setPcapLatest] = useState<LatestPcapSummary | null>(null)
  const [pcapLoading, setPcapLoading] = useState(true)
  
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
      const [trafficResponse, criticalResponse, pcapStats] = await Promise.all([
        flaskApi.getTrafficStats(),
        flaskApi.getCriticalAlerts().catch(() => ({ unresolved_count: 0 })),
        flaskApi.getPcapStats().catch(() => ({ total_detections: 0, critical_detections: 0 })),
      ])

      const trafficSummary = (trafficResponse as { summary?: { total_anomalies?: number } }).summary
      const baseTotal = realtimeData?.summary?.total_anomalies || trafficSummary?.total_anomalies || 0
      const baseCritical = criticalResponse.unresolved_count || 0

      const data = {
        totalAlerts: baseTotal + (pcapStats?.total_detections ?? 0),
        criticalAlerts: baseCritical + (pcapStats?.critical_detections ?? 0),
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

  // Fetch latest PCAP analysis for dashboard card
  const fetchLatestPcap = useCallback(async () => {
    setPcapLoading(true)
    try {
      const data = await flaskApi.getLastPcapAnalysis()
      if (data && !("error" in data)) {
        setPcapLatest(data as LatestPcapSummary)
      } else {
        setPcapLatest(null)
      }
    } catch {
      setPcapLatest(null)
    } finally {
      setPcapLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  useEffect(() => {
    fetchLatestPcap()
  }, [fetchLatestPcap])

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

  // Memoize expensive computations (full number with locale formatting)
  const formattedPacketCount = useMemo(() => {
    return stats.totalPackets.toLocaleString()
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
                {formattedPacketCount}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Analyzed</p>
            </CardContent>
          </Card>
        </div>

        {/* Latest PCAP Analysis card */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileSearch className="h-4 w-4" />
              Latest PCAP Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pcapLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : !pcapLatest ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-muted-foreground">No PCAP analysis yet.</p>
                <Button asChild variant="outline" size="sm" className="w-fit">
                  <Link href="/analysis" className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" />
                    Upload and analyze a PCAP
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <span className="text-xs text-muted-foreground">Risk</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-lg font-semibold">{pcapLatest.risk?.score ?? "--"}</span>
                    <Badge variant={pcapLatest.risk?.level === "high" || pcapLatest.risk?.level === "critical" ? "destructive" : "secondary"}>
                      {(pcapLatest.risk?.level ?? "low").toUpperCase()}
                    </Badge>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Packets</span>
                  <div className="text-lg font-semibold mt-0.5">{pcapLatest.metadata?.packets_processed ?? "--"}</div>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Detections</span>
                  <div className="text-lg font-semibold mt-0.5">{pcapLatest.detections?.length ?? 0}</div>
                </div>
                {pcapLatest.metadata?.filename && (
                  <p className="text-xs text-muted-foreground truncate max-w-[180px]" title={pcapLatest.metadata.filename}>
                    {pcapLatest.metadata.filename}
                  </p>
                )}
                <Button asChild variant="outline" size="sm" className="ml-auto">
                  <Link href="/analysis" className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" />
                    View full analysis
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-6">
          <Suspense fallback={<div className="h-96 flex items-center justify-center">Loading alerts...</div>}>
            <AlertsOverview />
          </Suspense>
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
