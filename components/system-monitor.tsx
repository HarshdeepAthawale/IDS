"use client"

import { useState, useEffect, useCallback, memo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Server, Database, Cpu, AlertTriangle } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { useWebSocket } from "@/hooks/use-websocket"
import { useDebounce } from "@/hooks/use-debounce"

interface SystemInfo {
  system_info: {
    python_version: string
    flask_version: string
    scapy_version: string
  }
  configuration: {
    capture_interface: string
    packet_rate_threshold: number
    connection_limit: number
    anomaly_score_threshold: number
    whitelist_ips: string[]
    alert_dedup_window: number
  }
  database_info: {
    type: string
    url: string
  }
}

interface AnomalyStats {
  anomaly_stats: {
    total_anomalies: number
    anomalies_per_hour: number
    peak_anomalies: number
    current_anomaly_rate: number
  }
  severity_distribution: Record<string, number>
}

interface ConnectionStats {
  connection_stats: {
    total_connections: number
    active_connections: number
    successful_connections: number
    failed_connections: number
    connection_success_rate: number
    avg_connection_duration: number
    top_source_ips: Array<{ ip: string; count: number }>
    top_dest_ports: Array<{ port: string; count: number }>
  }
  connection_trend: Array<{
    timestamp: string
    active_connections: number
    successful_connections: number
    failed_connections: number
  }>
}

function SystemMonitor() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [anomalyStats, setAnomalyStats] = useState<AnomalyStats | null>(null)
  const [connectionStats, setConnectionStats] = useState<ConnectionStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchErrors, setFetchErrors] = useState<{
    system?: string
    anomalies?: string
    connections?: string
  }>({})
  
  // Real-time WebSocket connection
  const { isConnected, isConnecting, on, off } = useWebSocket({ room: 'dashboard' })
  
  // Debounced state for updates
  const [pendingAnomalyUpdate, setPendingAnomalyUpdate] = useState<Partial<AnomalyStats['anomaly_stats']> | null>(null)
  const [pendingConnectionUpdate, setPendingConnectionUpdate] = useState<Partial<ConnectionStats['connection_stats']> | null>(null)
  const debouncedAnomalyUpdate = useDebounce(pendingAnomalyUpdate, 100)
  const debouncedConnectionUpdate = useDebounce(pendingConnectionUpdate, 100)

  const fetchSystemData = useCallback(async () => {
    const errors: typeof fetchErrors = {}
    let hasSuccess = false
    
    try {
      // Fetch each endpoint independently to allow partial failures
      try {
        const system = await flaskApi.getSystemInfo()
        setSystemInfo(system)
        setFetchErrors(prev => ({ ...prev, system: undefined }))
        hasSuccess = true
      } catch (err) {
        console.error('Error fetching system info:', err)
        const errorMsg = err instanceof Error && err.message.includes('Network error') 
          ? 'Backend disconnected' 
          : 'Failed to fetch system info'
        errors.system = errorMsg
        setFetchErrors(prev => ({ ...prev, system: errorMsg }))
      }

      try {
        const anomalies = await flaskApi.getAnomalyStats({ hours: 24 })
        setAnomalyStats(anomalies)
        setFetchErrors(prev => ({ ...prev, anomalies: undefined }))
        hasSuccess = true
      } catch (err) {
        console.error('Error fetching anomaly stats:', err)
        const errorMsg = err instanceof Error && err.message.includes('Network error')
          ? 'Backend disconnected'
          : 'Failed to fetch anomaly stats'
        errors.anomalies = errorMsg
        setFetchErrors(prev => ({ ...prev, anomalies: errorMsg }))
      }

      try {
        const connections = await flaskApi.getConnectionStats({ hours: 24 })
        setConnectionStats(connections)
        setFetchErrors(prev => ({ ...prev, connections: undefined }))
        hasSuccess = true
      } catch (err) {
        console.error('Error fetching connection stats:', err)
        const errorMsg = err instanceof Error && err.message.includes('Network error')
          ? 'Backend disconnected'
          : 'Failed to fetch connection stats'
        errors.connections = errorMsg
        setFetchErrors(prev => ({ ...prev, connections: errorMsg }))
      }

      // Only show error if backend is disconnected AND all requests failed
      if (!hasSuccess && !isConnected && !isConnecting) {
        setError('Failed to fetch system information. Please ensure the backend is running.')
      } else {
        setError(null)
      }
      
      setFetchErrors(errors)
    } catch (err) {
      console.error('Unexpected error fetching system data:', err)
      // Only set error if backend is definitely disconnected
      if (!isConnected && !isConnecting && !hasSuccess) {
        setError('Failed to fetch system information')
      }
    } finally {
      setLoading(false)
    }
  }, [isConnected, isConnecting])

  // Initial fetch
  useEffect(() => {
    fetchSystemData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  // Clear error when WebSocket connects
  useEffect(() => {
    if (isConnected && error) {
      setError(null)
    }
  }, [isConnected, error])

  // Apply debounced anomaly stats updates
  useEffect(() => {
    if (debouncedAnomalyUpdate && anomalyStats) {
      setAnomalyStats(prev => prev ? {
        ...prev,
        anomaly_stats: {
          ...prev.anomaly_stats,
          ...debouncedAnomalyUpdate
        }
      } : null)
      setPendingAnomalyUpdate(null)
    }
  }, [debouncedAnomalyUpdate, anomalyStats])

  // Apply debounced connection stats updates
  useEffect(() => {
    if (debouncedConnectionUpdate && connectionStats) {
      setConnectionStats(prev => prev ? {
        ...prev,
        connection_stats: {
          ...prev.connection_stats,
          ...debouncedConnectionUpdate
        }
      } : null)
      setPendingConnectionUpdate(null)
    }
  }, [debouncedConnectionUpdate, connectionStats])

  // Real-time WebSocket updates (with debouncing)
  useEffect(() => {
    if (!isConnected) {
      // Only use polling as true fallback when WebSocket is disconnected
      const fallbackInterval = setInterval(() => {
        fetchSystemData()
      }, 10000)
      return () => clearInterval(fallbackInterval)
    }

    const handleSystemUpdate = (data: any) => {
      const updateData = data.data || data
      
      // Queue anomaly stats update (will be debounced)
      if (updateData.anomaly_stats) {
        setPendingAnomalyUpdate(updateData.anomaly_stats)
      }
      
      // Queue connection stats update (will be debounced)
      if (updateData.connection_stats) {
        setPendingConnectionUpdate(updateData.connection_stats)
      }
    }

    const handleTrafficUpdate = (data: any) => {
      const trafficData = data.data || data
      
      // Queue connection stats update from traffic updates (will be debounced)
      if (trafficData.active_connections !== undefined) {
        setPendingConnectionUpdate({ active_connections: trafficData.active_connections })
      }
    }

    on('system_update', handleSystemUpdate)
    on('traffic_update', handleTrafficUpdate)
    on('stats_update', handleSystemUpdate)

    return () => {
      off('system_update', handleSystemUpdate)
      off('traffic_update', handleTrafficUpdate)
      off('stats_update', handleSystemUpdate)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]) // on/off are stable from context

  if (loading) {
    return (
      <Card className="bg-card border-border">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Activity className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading system information...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Only show error if backend is disconnected and we have no data at all
  if (error && !isConnected && !isConnecting && !systemInfo && !anomalyStats && !connectionStats) {
    return (
      <Card className="bg-card border-border">
        <CardContent className="p-6">
          <div className="flex items-center text-destructive">
            <AlertTriangle className="h-5 w-5 mr-2" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* System Information */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Server className="h-5 w-5 text-blue-500" />
            System Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {systemInfo && (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Python Version</span>
                <Badge variant="outline">{systemInfo.system_info.python_version}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Flask Version</span>
                <Badge variant="outline">{systemInfo.system_info.flask_version}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Scapy Version</span>
                <Badge variant="outline">{systemInfo.system_info.scapy_version}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Capture Interface</span>
                <Badge variant="outline">{systemInfo.configuration.capture_interface}</Badge>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Database Information */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Database className="h-5 w-5 text-green-500" />
            Database
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {systemInfo && (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Type</span>
                <Badge variant="outline">{systemInfo.database_info.type}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Connection Limit</span>
                <Badge variant="outline">{systemInfo.configuration.connection_limit}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Dedup Window</span>
                <Badge variant="outline">{systemInfo.configuration.alert_dedup_window}s</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Whitelist IPs</span>
                <Badge variant="outline">{systemInfo.configuration.whitelist_ips.length}</Badge>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Anomaly Statistics */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Cpu className="h-5 w-5 text-orange-500" />
            Anomaly Detection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {anomalyStats && (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Total Anomalies</span>
                <Badge variant="outline">{anomalyStats.anomaly_stats.total_anomalies}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Per Hour</span>
                <Badge variant="outline">{anomalyStats.anomaly_stats.anomalies_per_hour.toFixed(2)}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Peak Anomalies</span>
                <Badge variant="outline">{anomalyStats.anomaly_stats.peak_anomalies}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Current Rate</span>
                <Badge variant="outline">{anomalyStats.anomaly_stats.current_anomaly_rate.toFixed(2)}</Badge>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Connection Statistics */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5 text-purple-500" />
            Connections
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {connectionStats && (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Active</span>
                <Badge variant="outline">{connectionStats.connection_stats.active_connections}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Success Rate</span>
                <Badge variant="outline">{(connectionStats.connection_stats.connection_success_rate * 100).toFixed(1)}%</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Total</span>
                <Badge variant="outline">{connectionStats.connection_stats.total_connections}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Avg Duration</span>
                <Badge variant="outline">{connectionStats.connection_stats.avg_connection_duration.toFixed(1)}s</Badge>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default memo(SystemMonitor)
