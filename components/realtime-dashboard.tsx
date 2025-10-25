"use client"

import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Activity, Wifi, WifiOff, RefreshCw, Bell, BellOff } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts"
import { config } from "@/lib/config"

interface RealtimeData {
  timestamp: string
  packetsPerSecond: number
  threatsDetected: number
  connectionsActive: number
  bandwidthUsed: number
}

interface LiveAlert {
  id: string
  timestamp: string
  severity: "critical" | "high" | "medium" | "low"
  type: string
  description: string
  sourceIp: string
  destIp: string
}

export default function RealtimeDashboard() {
  const [isConnected, setIsConnected] = useState(false)
  const [notificationsEnabled, setNotificationsEnabled] = useState(true)
  const [realtimeData, setRealtimeData] = useState<RealtimeData[]>([])
  const [liveAlerts, setLiveAlerts] = useState<LiveAlert[]>([])
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("disconnected")
  const [error, setError] = useState<string | null>(null)
  
  const socketRef = useRef<WebSocket | null>(null)
  const maxDataPoints = 50

  const connectWebSocket = () => {
    try {
      setConnectionStatus("connecting")
      setError(null)
      
      // Connect to Flask SocketIO server
      const wsUrl = `ws://localhost:3002/socket.io/?EIO=4&transport=websocket`
      socketRef.current = new WebSocket(wsUrl)
      
      socketRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionStatus("connected")
        
        // Send authentication if needed
        socketRef.current?.send(JSON.stringify({
          type: 'auth',
          token: 'dashboard_token'
        }))
      }
      
      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleRealtimeData(data)
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }
      
      socketRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        setConnectionStatus("disconnected")
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (connectionStatus !== "connected") {
            connectWebSocket()
          }
        }, 5000)
      }
      
      socketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus("error")
        setError("Failed to connect to real-time server")
      }
      
    } catch (err) {
      console.error('Error connecting WebSocket:', err)
      setConnectionStatus("error")
      setError("WebSocket connection failed")
    }
  }

  const disconnectWebSocket = () => {
    if (socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
    setIsConnected(false)
    setConnectionStatus("disconnected")
  }

  const handleRealtimeData = useCallback((data: any) => {
    switch (data.type) {
      case 'traffic_update':
        const newDataPoint: RealtimeData = {
          timestamp: new Date().toISOString(),
          packetsPerSecond: data.packets_per_second || 0,
          threatsDetected: data.threats_detected || 0,
          connectionsActive: data.active_connections || 0,
          bandwidthUsed: data.bandwidth_mbps || 0
        }
        
        setRealtimeData(prev => {
          const updated = [...prev, newDataPoint]
          return updated.slice(-maxDataPoints)
        })
        break
        
      case 'new_alert':
        const newAlert: LiveAlert = {
          id: data.alert_id || Date.now().toString(),
          timestamp: new Date().toISOString(),
          severity: data.severity || "medium",
          type: data.alert_type || "Unknown",
          description: data.description || "New threat detected",
          sourceIp: data.source_ip || "Unknown",
          destIp: data.dest_ip || "Unknown"
        }
        
        setLiveAlerts(prev => [newAlert, ...prev.slice(0, 9)]) // Keep last 10 alerts
        
        // Show browser notification if enabled
        if (notificationsEnabled && 'Notification' in window) {
          if (Notification.permission === 'granted') {
            new Notification(`New ${newAlert.severity} Alert`, {
              body: newAlert.description,
              icon: '/favicon.ico'
            })
          } else if (Notification.permission !== 'denied') {
            Notification.requestPermission()
          }
        }
        break
        
      default:
        console.log('Unknown message type:', data.type)
    }
  }, [notificationsEnabled])

  const requestNotificationPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }

  useEffect(() => {
    // Request notification permission on mount
    requestNotificationPermission()
    
    // Connect to WebSocket
    connectWebSocket()
    
    // Cleanup on unmount
    return () => {
      disconnectWebSocket()
    }
  }, [])

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-destructive/10 text-destructive"
      case "high":
        return "bg-orange-500/10 text-orange-500"
      case "medium":
        return "bg-yellow-500/10 text-yellow-500"
      default:
        return "bg-green-500/10 text-green-500"
    }
  }

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "text-green-500"
      case "connecting":
        return "text-yellow-500"
      case "error":
        return "text-destructive"
      default:
        return "text-muted-foreground"
    }
  }

  const formatTime = useCallback((timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }, [])

  const chartData = useMemo(() => {
    return realtimeData.map(point => ({
      time: formatTime(point.timestamp),
      packets: point.packetsPerSecond,
      threats: point.threatsDetected,
      connections: point.connectionsActive,
      bandwidth: point.bandwidthUsed
    }))
  }, [realtimeData, formatTime])

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <Wifi className="h-5 w-5 text-green-500" />
              ) : (
                <WifiOff className="h-5 w-5 text-muted-foreground" />
              )}
              Real-time Connection
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                className="flex items-center gap-1"
              >
                {notificationsEnabled ? (
                  <Bell className="h-4 w-4" />
                ) : (
                  <BellOff className="h-4 w-4" />
                )}
                {notificationsEnabled ? "Notifications On" : "Notifications Off"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={isConnected ? disconnectWebSocket : connectWebSocket}
                disabled={connectionStatus === "connecting"}
                className="flex items-center gap-1"
              >
                {connectionStatus === "connecting" ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Activity className="h-4 w-4" />
                )}
                {isConnected ? "Disconnect" : "Connect"}
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-gray-400'
              }`} />
              <span className={`text-sm font-medium ${getConnectionStatusColor()}`}>
                {connectionStatus === "connecting" && "Connecting..."}
                {connectionStatus === "connected" && "Connected"}
                {connectionStatus === "disconnected" && "Disconnected"}
                {connectionStatus === "error" && "Connection Error"}
              </span>
            </div>
            {error && (
              <span className="text-sm text-destructive">{error}</span>
            )}
            {realtimeData.length > 0 && (
              <Badge variant="outline">
                {realtimeData.length} data points
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Real-time Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Traffic Chart */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              Live Traffic
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  labelStyle={{ fontSize: 12 }}
                  contentStyle={{ fontSize: 12 }}
                />
                <Line 
                  type="monotone" 
                  dataKey="packets" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  name="Packets/sec"
                />
                <Line 
                  type="monotone" 
                  dataKey="threats" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                  name="Threats"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Connections Chart */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wifi className="h-5 w-5 text-green-500" />
              Active Connections
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  labelStyle={{ fontSize: 12 }}
                  contentStyle={{ fontSize: 12 }}
                />
                <Bar 
                  dataKey="connections" 
                  fill="#10b981" 
                  name="Active Connections"
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Live Alerts */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            Live Alerts ({liveAlerts.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {liveAlerts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No live alerts. Waiting for real-time data...</p>
            </div>
          ) : (
            <div className="space-y-3">
              {liveAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="p-3 rounded-lg bg-background border border-border animate-in slide-in-from-top-2 duration-300"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-semibold px-2 py-1 rounded ${getSeverityColor(alert.severity)}`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-muted-foreground">{alert.type}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatTime(alert.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-foreground mb-1">{alert.description}</p>
                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span>From: {alert.sourceIp}</span>
                    <span>To: {alert.destIp}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
