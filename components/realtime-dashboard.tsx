"use client"

import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { io, Socket } from "socket.io-client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Activity, Wifi, WifiOff, RefreshCw, Bell, BellOff } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from "recharts"
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
  
  const socketRef = useRef<Socket | null>(null)
  const handleRealtimeDataRef = useRef<(data: any) => void>()
  const maxDataPoints = 50

  // Store handleRealtimeData in ref to always have latest version
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
        console.log('[Frontend] Processing new alert:', data)
        const newAlert: LiveAlert = {
          id: data.alert_id || Date.now().toString(),
          timestamp: new Date().toISOString(),
          severity: data.severity || "medium",
          type: data.alert_type || "Unknown",
          description: data.description || "New threat detected",
          sourceIp: data.source_ip || "Unknown",
          destIp: data.dest_ip || "Unknown"
        }
        
        console.log('[Frontend] Adding alert to state:', newAlert)
        setLiveAlerts(prev => {
          const updated = [newAlert, ...prev.slice(0, 9)] // Keep last 10 alerts
          console.log('[Frontend] Updated liveAlerts count:', updated.length)
          return updated
        })
        
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
  }, [notificationsEnabled, maxDataPoints])

  // Update ref whenever handleRealtimeData changes
  useEffect(() => {
    handleRealtimeDataRef.current = handleRealtimeData
  }, [handleRealtimeData])

  const connectWebSocket = useCallback(() => {
    try {
      // Clean up existing connection if any
      if (socketRef.current) {
        socketRef.current.removeAllListeners()
        socketRef.current.disconnect()
        socketRef.current = null
      }

      setConnectionStatus("connecting")
      setError(null)
      
      // Use socket.io-client for Flask-SocketIO compatibility
      const socket = io('http://localhost:3002', {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5
      })
      
      socketRef.current = socket
      
      socket.on('connect', () => {
        console.log('Socket.IO connected')
        setIsConnected(true)
        setConnectionStatus("connected")
        
        // Join dashboard room
        socket.emit('join_room', { room: 'dashboard' })
      })
      
      socket.on('connected', (data: any) => {
        console.log('Server confirmed connection:', data)
      })
      
      socket.on('new_alert', (data: any) => {
        console.log('[WebSocket] new_alert event received:', data)
        // Use ref to get latest version of handleRealtimeData
        if (handleRealtimeDataRef.current) {
          handleRealtimeDataRef.current({
            type: 'new_alert',
            alert_id: data.alert_id || data.id || Date.now().toString(),
            severity: data.severity || 'medium',
            alert_type: data.alert_type || data.type || 'Unknown',
            description: data.description || 'New threat detected',
            source_ip: data.source_ip || 'Unknown',
            dest_ip: data.dest_ip || 'Unknown'
          })
        }
      })
      
      socket.on('traffic_update', (data: any) => {
        const packetsPerSecond = data.packets_per_second || data.packet_rate || 0
        console.log('[WebSocket] traffic_update event received:', {
          packets_per_second: packetsPerSecond,
          threats_detected: data.threats_detected || 0,
          active_connections: data.active_connections || 0,
          total_packets: data.total_packets || 0,
          timestamp: data.timestamp
        })
        // Use ref to get latest version of handleRealtimeData
        if (handleRealtimeDataRef.current) {
          handleRealtimeDataRef.current({
            type: 'traffic_update',
            packets_per_second: packetsPerSecond,
            threats_detected: data.threats_detected || 0,
            active_connections: data.active_connections || 0,
            bandwidth_mbps: data.bandwidth_mbps || 0
          })
        }
      })
      
      socket.on('disconnect', () => {
        console.log('Socket.IO disconnected')
        setIsConnected(false)
        setConnectionStatus("disconnected")
      })
      
      socket.on('connect_error', (error: Error) => {
        console.error('Socket.IO connection error:', error)
        setConnectionStatus("error")
        setError("Failed to connect to real-time server. Backend may not be running.")
      })
      
    } catch (err) {
      console.error('Error connecting Socket.IO:', err)
      setConnectionStatus("error")
      setError("Socket.IO connection failed. Make sure socket.io-client is installed.")
    }
  }, [])

  const disconnectWebSocket = () => {
    if (socketRef.current) {
      socketRef.current.emit('leave_room', { room: 'dashboard' })
      socketRef.current.disconnect()
      socketRef.current = null
    }
    setIsConnected(false)
    setConnectionStatus("disconnected")
  }


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
  }, [connectWebSocket])

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
            {chartData.length === 0 ? (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                <div className="text-center">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Waiting for traffic data...</p>
                  <p className="text-xs mt-1">WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</p>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    domain={[0, 'auto']}
                  />
                  <Tooltip 
                    labelStyle={{ fontSize: 12 }}
                    contentStyle={{ fontSize: 12 }}
                    formatter={(value: any) => {
                      if (typeof value === 'number') {
                        return value.toFixed(2)
                      }
                      return value
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ fontSize: 12 }}
                    iconType="line"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="packets" 
                    stroke="#06b6d4" 
                    strokeWidth={3}
                    name="Packets/sec"
                    dot={{ fill: "#06b6d4", r: 4 }}
                    activeDot={{ r: 6 }}
                    legendType="line"
                    connectNulls={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="threats" 
                    stroke="#ef4444" 
                    strokeWidth={2}
                    name="Threats Detected"
                    dot={false}
                    legendType="line"
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
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
              <p className="font-medium mb-2">No live alerts detected</p>
              <p className="text-sm">System is monitoring network traffic. Alerts will appear here when threats are detected.</p>
              <p className="text-xs mt-2 opacity-75">
                Connection: {isConnected ? 'Connected' : 'Disconnected'} • 
                WebSocket: {connectionStatus}
              </p>
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
