"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Server, Database, Cpu, AlertTriangle } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"

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

export default function SystemMonitor() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [anomalyStats, setAnomalyStats] = useState<AnomalyStats | null>(null)
  const [connectionStats, setConnectionStats] = useState<ConnectionStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSystemData = async () => {
    try {
      setError(null)
      const [system, anomalies, connections] = await Promise.all([
        flaskApi.getSystemInfo(),
        flaskApi.getAnomalyStats({ hours: 24 }),
        flaskApi.getConnectionStats({ hours: 24 })
      ])
      
      setSystemInfo(system)
      setAnomalyStats(anomalies)
      setConnectionStats(connections)
    } catch (err) {
      console.error('Error fetching system data:', err)
      setError('Failed to fetch system information')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSystemData()
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchSystemData, 30000)
    return () => clearInterval(interval)
  }, [])

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

  if (error) {
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
