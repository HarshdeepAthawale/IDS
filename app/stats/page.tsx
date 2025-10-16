"use client"

import { useState, useEffect } from "react"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  BarChart,
  Bar,
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

interface TrafficData {
  time: string
  packets: number
  bytes: number
}

interface ProtocolData {
  name: string
  value: number
}

interface ConnectionData {
  protocol: string
  count: number
}

export default function StatsPage() {
  const [trafficData, setTrafficData] = useState<TrafficData[]>([])
  const [protocolData, setProtocolData] = useState<ProtocolData[]>([])
  const [connectionData, setConnectionData] = useState<ConnectionData[]>([])

  useEffect(() => {
    // Simulate fetching traffic stats from Flask backend
    const mockTrafficData: TrafficData[] = [
      { time: "00:00", packets: 4200, bytes: 1024000 },
      { time: "04:00", packets: 3800, bytes: 950000 },
      { time: "08:00", packets: 5200, bytes: 1280000 },
      { time: "12:00", packets: 6100, bytes: 1500000 },
      { time: "16:00", packets: 5800, bytes: 1420000 },
      { time: "20:00", packets: 4900, bytes: 1200000 },
    ]

    const mockProtocolData: ProtocolData[] = [
      { name: "TCP", value: 45 },
      { name: "UDP", value: 30 },
      { name: "ICMP", value: 15 },
      { name: "DNS", value: 10 },
    ]

    const mockConnectionData: ConnectionData[] = [
      { protocol: "HTTP", count: 2450 },
      { protocol: "HTTPS", count: 3120 },
      { protocol: "SSH", count: 890 },
      { protocol: "FTP", count: 340 },
      { protocol: "SMTP", count: 560 },
    ]

    setTrafficData(mockTrafficData)
    setProtocolData(mockProtocolData)
    setConnectionData(mockConnectionData)
  }, [])

  const COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"]

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Traffic Statistics</h1>
          <p className="text-muted-foreground mt-2">Network traffic analysis and metrics</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Packets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">29.9M</div>
              <p className="text-xs text-muted-foreground mt-1">Last 24 hours</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Data</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">7.4GB</div>
              <p className="text-xs text-muted-foreground mt-1">Transferred</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Packet Size</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">247KB</div>
              <p className="text-xs text-muted-foreground mt-1">Per packet</p>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Traffic Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trafficData}>
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
            <CardHeader>
              <CardTitle>Protocol Distribution</CardTitle>
            </CardHeader>
            <CardContent>
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
                  >
                    {protocolData.map((entry, index) => (
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

        {/* Active Connections */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle>Active Connections by Protocol</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={connectionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="protocol" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                  labelStyle={{ color: "#f3f4f6" }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}
