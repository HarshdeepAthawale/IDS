"use client"

import { useState, useEffect, useCallback } from "react"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle } from "lucide-react"
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { flaskApi, transformers } from "@/lib/flask-api"
import { useWebSocket } from "@/hooks/use-websocket"

interface ProtocolData {
  name: string
  value: number
}

interface ConnectionData {
  protocol: string
  count: number
}

export default function StatsPage() {
  const [protocolData, setProtocolData] = useState<ProtocolData[]>([])
  const [connectionData, setConnectionData] = useState<ConnectionData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<any>(null)
  
  // Real-time WebSocket connection
  const { isConnected } = useWebSocket({ room: 'dashboard' })

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [trafficResponse, protocolResponse, connectionResponse] = await Promise.all([
        flaskApi.getTrafficStats({ hours: 24, limit: 24 }),
        flaskApi.getProtocolStats({ hours: 24, limit: 10 }),
        flaskApi.getConnectionStats({ hours: 24, limit: 20 })
      ])

      // Transform protocol data
      const transformedProtocols = transformers.protocolStatsToFrontend(protocolResponse.protocol_distribution || {})
      setProtocolData(transformedProtocols)

      // Transform connection data
      const transformedConnections = transformers.connectionStatsToFrontend(connectionResponse)
      setConnectionData(transformedConnections)

      // Set summary for stats cards
      setSummary({
        totalPackets: trafficResponse.current_stats?.total_packets || 0,
        totalBytes: trafficResponse.current_stats?.total_bytes || 0,
        avgPacketSize: trafficResponse.current_stats?.avg_packet_size || 0,
      })

    } catch (err) {
      console.error('Error fetching stats:', err)
      setError('Failed to fetch statistics. Backend may be unavailable.')
      setProtocolData([])
      setConnectionData([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    
    // Only poll if WebSocket is not connected (true fallback)
    let interval: NodeJS.Timeout | null = null
    if (!isConnected) {
      interval = setInterval(fetchStats, 30000)
    }
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [fetchStats, isConnected])

  const COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"]

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Traffic Statistics</h1>
          <p className="text-muted-foreground mt-2">Network traffic analysis and metrics</p>
        </div>

        {error && (
          <div className="border rounded-md p-4 bg-destructive/10 border-destructive/20">
            <div className="flex items-start">
              <AlertCircle className="h-5 w-5 text-destructive mr-3 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-destructive">Error Loading Statistics</p>
                <p className="text-sm text-destructive/80 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Packets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">
                {loading ? '...' : summary ? summary.totalPackets.toLocaleString() : '0'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Last 24 hours</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Data</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">
                {loading ? '...' : summary ? (summary.totalBytes / (1024 * 1024 * 1024)).toFixed(2) + 'GB' : '0GB'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Transferred</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Packet Size</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">
                {loading ? '...' : summary ? (summary.avgPacketSize / 1024).toFixed(1) + 'KB' : '0KB'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Per packet</p>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Protocol Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                  Loading protocol data...
                </div>
              ) : protocolData.length === 0 ? (
                <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                  No protocol data available
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                  <Pie
                    data={protocolData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name} ${value}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    isAnimationActive={true}
                    animationDuration={400}
                    animationEasing="ease-out"
                    activeIndex={undefined}
                    activeShape={{ 
                      outerRadius: 90, 
                      fill: "#3b82f6",
                      stroke: "#fff",
                      strokeWidth: 2
                    }}
                  >
                    {protocolData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                      labelStyle={{ color: "#f3f4f6" }}
                      animationDuration={200}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Active Connections */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle>Active Connections by Protocol</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                Loading connection data...
              </div>
            ) : connectionData.length === 0 ? (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                No connection data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={connectionData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="protocol" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                  labelStyle={{ color: "#f3f4f6" }}
                  cursor={{ fill: "rgba(59, 130, 246, 0.1)" }}
                  animationDuration={200}
                />
                  <Bar 
                    dataKey="count" 
                    fill="#3b82f6" 
                    radius={[8, 8, 0, 0]}
                    isAnimationActive={true}
                    animationDuration={400}
                    animationEasing="ease-out"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}
