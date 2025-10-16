"use client"

import { useState, useEffect } from "react"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, Download } from "lucide-react"

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

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [filterType, setFilterType] = useState<"all" | "signature" | "anomaly">("all")
  const [filterSeverity, setFilterSeverity] = useState<"all" | "critical" | "high" | "medium" | "low">("all")

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
      {
        id: "5",
        timestamp: new Date(Date.now() - 60 * 60000).toISOString(),
        sourceIp: "10.0.0.15",
        destIp: "203.0.113.100",
        protocol: "HTTPS",
        type: "signature",
        severity: "low",
        description: "Suspicious Port Scan",
      },
    ]
    setAlerts(mockAlerts)
  }, [])

  const filteredAlerts = alerts.filter((alert) => {
    const typeMatch = filterType === "all" || alert.type === filterType
    const severityMatch = filterSeverity === "all" || alert.severity === filterSeverity
    return typeMatch && severityMatch
  })

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-destructive bg-destructive/10"
      case "high":
        return "text-orange-500 bg-orange-500/10"
      case "medium":
        return "text-yellow-500 bg-yellow-500/10"
      default:
        return "text-green-500 bg-green-500/10"
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Alerts</h1>
            <p className="text-muted-foreground mt-2">View and manage all network alerts</p>
          </div>
          <Button className="gap-2">
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>

        {/* Filters */}
        <Card className="bg-card border-border">
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              <div>
                <label className="text-sm font-medium text-foreground block mb-2">Alert Type</label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value as any)}
                  className="px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm"
                >
                  <option value="all">All Types</option>
                  <option value="signature">Signature</option>
                  <option value="anomaly">Anomaly</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground block mb-2">Severity</label>
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value as any)}
                  className="px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Alerts Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              All Alerts ({filteredAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Timestamp</th>
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Source IP</th>
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Dest IP</th>
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Protocol</th>
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Type</th>
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Severity</th>
                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAlerts.map((alert) => (
                    <tr key={alert.id} className="border-b border-border hover:bg-background/50 transition-colors">
                      <td className="py-3 px-4 text-muted-foreground">{new Date(alert.timestamp).toLocaleString()}</td>
                      <td className="py-3 px-4 text-foreground font-mono text-xs">{alert.sourceIp}</td>
                      <td className="py-3 px-4 text-foreground font-mono text-xs">{alert.destIp}</td>
                      <td className="py-3 px-4 text-foreground">{alert.protocol}</td>
                      <td className="py-3 px-4 text-foreground capitalize">{alert.type}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-foreground">{alert.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}
