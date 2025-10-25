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
    // Fetch insider threats from Flask backend
    const fetchInsiderThreats = async () => {
      try {
        const response = await fetch('/api/insider/summary')
        if (response.ok) {
          const data = await response.json()
          // Transform Flask activities to match our interface
          const transformedThreats = (data.activities || []).map((activity: any) => ({
            id: activity.id.toString(),
            timestamp: activity.timestamp,
            user: activity.username,
            activity: activity.activity_type,
            riskLevel: activity.severity,
            details: activity.description
          }))
          setThreats(transformedThreats)
        } else {
          console.error('Failed to fetch insider threats')
          setThreats([])
        }
      } catch (error) {
        console.error('Error fetching insider threats:', error)
        setThreats([])
      }
    }

    fetchInsiderThreats()
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
