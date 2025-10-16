"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle } from "lucide-react"

interface InsiderThreat {
  id: string
  timestamp: string
  user: string
  activity: string
  riskLevel: "critical" | "high" | "medium" | "low"
}

export default function InsiderThreatsOverview() {
  const [threats, setThreats] = useState<InsiderThreat[]>([])

  useEffect(() => {
    // Simulate fetching insider threats from Flask backend
    const mockThreats: InsiderThreat[] = [
      {
        id: "1",
        timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
        user: "john.doe@company.com",
        activity: "Accessed sensitive files outside work hours",
        riskLevel: "high",
      },
      {
        id: "2",
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
        user: "jane.smith@company.com",
        activity: "Downloaded large dataset to USB",
        riskLevel: "critical",
      },
      {
        id: "3",
        timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
        user: "bob.wilson@company.com",
        activity: "Multiple failed login attempts",
        riskLevel: "medium",
      },
    ]
    setThreats(mockThreats)
  }, [])

  const getRiskColor = (level: string) => {
    switch (level) {
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

  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          Insider Threats
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {threats.map((threat) => (
            <div key={threat.id} className="p-3 rounded-lg bg-background border border-border">
              <div className="flex items-start justify-between mb-2">
                <span className={`text-xs font-semibold px-2 py-1 rounded ${getRiskColor(threat.riskLevel)}`}>
                  {threat.riskLevel.toUpperCase()}
                </span>
                <span className="text-xs text-muted-foreground">{new Date(threat.timestamp).toLocaleTimeString()}</span>
              </div>
              <p className="text-sm font-medium text-foreground mb-1">{threat.user}</p>
              <p className="text-xs text-muted-foreground">{threat.activity}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
