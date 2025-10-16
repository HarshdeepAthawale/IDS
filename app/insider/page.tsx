"use client"

import { useState, useEffect } from "react"
import Layout from "@/components/layout"
import { Card, CardContent } from "@/components/ui/card"
import { AlertTriangle } from "lucide-react"

interface InsiderThreat {
  id: string
  timestamp: string
  user: string
  activity: string
  riskLevel: "critical" | "high" | "medium" | "low"
  details: string
}

export default function InsiderPage() {
  const [threats, setThreats] = useState<InsiderThreat[]>([])
  const [filterRisk, setFilterRisk] = useState<"all" | "critical" | "high" | "medium" | "low">("all")

  useEffect(() => {
    // Simulate fetching insider threats from Flask backend
    const mockThreats: InsiderThreat[] = [
      {
        id: "1",
        timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
        user: "john.doe@company.com",
        activity: "Accessed sensitive files outside work hours",
        riskLevel: "high",
        details: "User accessed HR database at 2:30 AM from home IP",
      },
      {
        id: "2",
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
        user: "jane.smith@company.com",
        activity: "Downloaded large dataset to USB",
        riskLevel: "critical",
        details: "2.3GB of customer data transferred to external device",
      },
      {
        id: "3",
        timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
        user: "bob.wilson@company.com",
        activity: "Multiple failed login attempts",
        riskLevel: "medium",
        details: "15 failed attempts to access admin panel in 5 minutes",
      },
      {
        id: "4",
        timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
        user: "alice.johnson@company.com",
        activity: "Unusual email forwarding rule created",
        riskLevel: "high",
        details: "New forwarding rule to external email address detected",
      },
      {
        id: "5",
        timestamp: new Date(Date.now() - 60 * 60000).toISOString(),
        user: "charlie.brown@company.com",
        activity: "Shared confidential document",
        riskLevel: "critical",
        details: "Financial report shared with external domain",
      },
    ]
    setThreats(mockThreats)
  }, [])

  const filteredThreats = threats.filter((threat) => {
    return filterRisk === "all" || threat.riskLevel === filterRisk
  })

  const getRiskColor = (level: string) => {
    switch (level) {
      case "critical":
        return "bg-destructive/10 text-destructive border-destructive/20"
      case "high":
        return "bg-orange-500/10 text-orange-500 border-orange-500/20"
      case "medium":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
      default:
        return "bg-green-500/10 text-green-500 border-green-500/20"
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Insider Threats</h1>
          <p className="text-muted-foreground mt-2">Monitor suspicious user activity and potential insider threats</p>
        </div>

        {/* Filters */}
        <Card className="bg-card border-border">
          <CardContent className="pt-6">
            <div>
              <label className="text-sm font-medium text-foreground block mb-2">Risk Level</label>
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value as any)}
                className="px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm"
              >
                <option value="all">All Risk Levels</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Threats Timeline */}
        <div className="space-y-4">
          {filteredThreats.map((threat) => (
            <Card key={threat.id} className={`bg-card border-2 ${getRiskColor(threat.riskLevel)}`}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4">
                    <AlertTriangle className="h-5 w-5 mt-1 flex-shrink-0" />
                    <div>
                      <h3 className="font-semibold text-foreground">{threat.user}</h3>
                      <p className="text-sm mt-1">{threat.activity}</p>
                    </div>
                  </div>
                  <span
                    className={`text-xs font-semibold px-3 py-1 rounded whitespace-nowrap ${getRiskColor(threat.riskLevel)}`}
                  >
                    {threat.riskLevel.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">{threat.details}</p>
                <div className="text-xs text-muted-foreground">{new Date(threat.timestamp).toLocaleString()}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </Layout>
  )
}
