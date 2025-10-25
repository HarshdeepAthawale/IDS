"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, RefreshCw, ExternalLink } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { config } from "@/lib/config"
import Link from "next/link"

interface InsiderThreat {
  id: string
  timestamp: string
  user: string
  userId: string
  activity: string
  riskLevel: "critical" | "high" | "medium" | "low"
  description?: string
}

export default function InsiderThreatsOverview() {
  const [threats, setThreats] = useState<InsiderThreat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchInsiderThreatsData = async () => {
    try {
      setError(null)
      const response = await flaskApi.getInsiderThreats()
      
      // Transform Flask activities to include userId
      const transformedThreats = (response.activities || []).map(activity => ({
        id: activity.id.toString(),
        timestamp: activity.timestamp,
        user: activity.username,
        userId: activity.user_id,
        activity: activity.activity_type,
        riskLevel: activity.severity,
        description: activity.description
      }))
      
      setThreats(transformedThreats)
    } catch (err) {
      console.error('Error fetching insider threats:', err)
      setError('Failed to fetch real-time insider threats')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchInsiderThreatsData()
    
    // Set up polling if enabled
    if (config.features.polling) {
      const interval = setInterval(fetchInsiderThreatsData, config.polling.dashboard)
      return () => clearInterval(interval)
    }
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
          {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
        </CardTitle>
        <button
          onClick={fetchInsiderThreatsData}
          disabled={loading}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
        >
          Refresh
        </button>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {threats.map((threat) => (
            <div key={threat.id} className="p-3 rounded-lg bg-background border border-border hover:border-primary/50 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <span className={`text-xs font-semibold px-2 py-1 rounded ${getRiskColor(threat.riskLevel)}`}>
                  {threat.riskLevel.toUpperCase()}
                </span>
                <span className="text-xs text-muted-foreground">{new Date(threat.timestamp).toLocaleTimeString()}</span>
              </div>
              <div className="flex items-center justify-between mb-1">
                <Link 
                  href={`/insider/users/${threat.userId}`}
                  className="text-sm font-medium text-foreground hover:text-primary transition-colors flex items-center gap-1"
                >
                  {threat.user}
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
              <p className="text-xs text-muted-foreground mb-1">{threat.activity}</p>
              {threat.description && (
                <p className="text-xs text-muted-foreground">{threat.description}</p>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
