"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { flaskApi } from "@/lib/flask-api"
import { config } from "@/lib/config"
import { RefreshCw } from "lucide-react"

interface TrafficData {
  time: string
  packets: number
  bytes: number
}

interface ProtocolData {
  name: string
  value: number
}

export default function TrafficStatsOverview() {
  const [trafficData, setTrafficData] = useState<TrafficData[]>([])
  const [protocolData, setProtocolData] = useState<ProtocolData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTrafficData = useCallback(async () => {
    try {
      setError(null)
      const response = await flaskApi.getTrafficStats()
      
      // Transform Flask response to frontend format
      const trafficData = response.historical_data.map(stat => ({
        time: new Date(stat.timestamp).toLocaleTimeString(),
        packets: stat.total_packets,
        bytes: stat.total_bytes,
      }))
      
      const protocolData = response.current_stats?.protocol_distribution 
        ? Object.entries(response.current_stats.protocol_distribution).map(([name, value]) => ({ name, value }))
        : []
      
      setTrafficData(trafficData)
      setProtocolData(protocolData)
    } catch (err) {
      console.error('Error fetching traffic stats:', err)
      setError('Failed to fetch real-time traffic data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTrafficData()
    
    // Set up polling if enabled - increased interval for better performance
    if (config.features.polling) {
      const interval = setInterval(fetchTrafficData, Math.max(config.polling.stats, 15000)) // Min 15 seconds
      return () => clearInterval(interval)
    }
  }, [fetchTrafficData])

  const COLORS = useMemo(() => ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"], [])

  // Memoize chart data to prevent unnecessary re-renders
  const chartData = useMemo(() => trafficData, [trafficData])
  const pieData = useMemo(() => protocolData, [protocolData])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            Traffic Trends
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardTitle>
          <button
            onClick={fetchTrafficData}
            disabled={loading}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            Refresh
          </button>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                labelStyle={{ color: "#f3f4f6" }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="packets"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: "#3b82f6", r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            Protocol Distribution
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name} ${value}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                labelStyle={{ color: "#f3f4f6" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
