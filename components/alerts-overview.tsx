"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle, TrendingUp } from "lucide-react"

interface Alert {
  id: string
  timestamp: string
  sourceIp: string
  destIp: string
  protocol: string
  type: "signature" | "anomaly"
  severity: "critical" | "high" | "medium" | "low"
  description: string
}

export default function AlertsOverview() {
  const [alerts, setAlerts] = useState<Alert[]>([])

  useEffect(() => {
    // Simulate fetching alerts from Flask backend
    const mockAlerts: Alert[] = [
      {
        id: "1",
        timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
        sourceIp: "192.168.1.105",
        destIp: "10.0.0.50",
        protocol: "TCP",
        type: "signature",
        severity: "critical",
        description: "SQL Injection Attempt Detected",
      },
      {
        id: "2",
        timestamp: new Date(Date.now() - 12 * 60000).toISOString(),
        sourceIp: "203.0.113.42",
        destIp: "10.0.0.100",
        protocol: "HTTP",
        type: "anomaly",
        severity: "high",
        description: "Unusual Data Transfer Pattern",
      },
      {
        id: "3",
        timestamp: new Date(Date.now() - 25 * 60000).toISOString(),
        sourceIp: "198.51.100.89",
        destIp: "10.0.0.75",
        protocol: "DNS",
        type: "signature",
        severity: "medium",
        description: "DNS Tunneling Detected",
      },
      {
        id: "4",
        timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
        sourceIp: "192.168.1.200",
        destIp: "10.0.0.25",
        protocol: "SSH",
        type: "anomaly",
        severity: "high",
        description: "Brute Force Attack Pattern",
      },
    ]
    setAlerts(mockAlerts)
  }, [])

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-destructive"
      case "high":
        return "text-orange-500"
      case "medium":
        return "text-yellow-500"
      default:
        return "text-green-500"
    }
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-destructive" />
          Recent Alerts
        </CardTitle>
        <TrendingUp className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-start justify-between p-3 rounded-lg bg-background border border-border hover:border-primary transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-sm font-semibold ${getSeverityColor(alert.severity)}`}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <span className="text-xs text-muted-foreground">{alert.type}</span>
                </div>
                <p className="text-sm font-medium text-foreground">{alert.description}</p>
                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                  <span>From: {alert.sourceIp}</span>
                  <span>To: {alert.destIp}</span>
                  <span>{alert.protocol}</span>
                </div>
              </div>
              <div className="text-xs text-muted-foreground ml-4 whitespace-nowrap">
                {new Date(alert.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
