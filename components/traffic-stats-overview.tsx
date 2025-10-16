"use client"

import { useState, useEffect } from "react"
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

    setTrafficData(mockTrafficData)
    setProtocolData(mockProtocolData)
  }, [])

  const COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"]

  return (
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
  )
}
