"use client"

import { useState, useEffect } from "react"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Users, Activity, TrendingUp, RefreshCw, BarChart3, Shield } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { format } from "date-fns"

interface AlertSummary {
  total_alerts?: number
  total_recent_alerts?: number
  unresolved_alerts: number
  alerts_by_severity: Record<string, number>
  alerts_by_type: Record<string, number>
  recent_trends?: Array<{
    date: string
    count: number
  }>
}

interface InsiderThreatsSummary {
  total_users: number
  suspicious_users: number
  high_risk_users: number
  activities_by_type: Record<string, number>
  risk_distribution: Record<string, number>
  top_threats: Array<{
    user_id: string
    username: string
    threat_count: number
    risk_level: string
  }>
}

export default function SummaryPage() {
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null)
  const [insiderSummary, setInsiderSummary] = useState<InsiderThreatsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSummaryData = async () => {
    try {
      setError(null)
      setLoading(true)
      
      const [alertData, insiderData] = await Promise.all([
        flaskApi.getAlertSummary(),
        flaskApi.getInsiderThreatsSummary()
      ])
      
      setAlertSummary(alertData)
      setInsiderSummary(insiderData)
    } catch (err) {
      console.error('Error fetching summary data:', err)
      setError('Failed to fetch summary data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSummaryData()
  }, [])

  const getSeverityColor = (severity: string) => {
    switch (severity) {
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

  const getRiskLevelColor = (level: string) => {
    switch (level) {
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
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Security Summary</h1>
            <p className="text-muted-foreground mt-2">Comprehensive overview of security metrics and threats</p>
          </div>
          <Button onClick={fetchSummaryData} disabled={loading} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Alert Summary */}
        {alertSummary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <AlertCircle className="h-5 w-5 text-destructive" />
                  Total Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-foreground">
                  {alertSummary.total_alerts ?? alertSummary.total_recent_alerts ?? 0}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {alertSummary.unresolved_alerts} unresolved
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Shield className="h-5 w-5 text-orange-500" />
                  Critical Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-destructive">
                  {alertSummary.alerts_by_severity?.critical || 0}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  High: {alertSummary.alerts_by_severity?.high || 0}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Activity className="h-5 w-5 text-blue-500" />
                  Alert Types
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Signature</span>
                    <Badge variant="outline">{alertSummary.alerts_by_type?.signature || 0}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Anomaly</span>
                    <Badge variant="outline">{alertSummary.alerts_by_type?.anomaly || 0}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                  Recent Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-foreground">
                  {alertSummary.recent_trends && alertSummary.recent_trends.length > 0
                    ? alertSummary.recent_trends[alertSummary.recent_trends.length - 1]?.count || 0
                    : 0}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  Last 5 days average
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Insider Threats Summary */}
        {insiderSummary && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-purple-500" />
                  User Risk Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-foreground">{insiderSummary.total_users}</div>
                    <div className="text-sm text-muted-foreground">Total Users</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-500">{insiderSummary.suspicious_users}</div>
                    <div className="text-sm text-muted-foreground">Suspicious</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-destructive">{insiderSummary.high_risk_users}</div>
                    <div className="text-sm text-muted-foreground">High Risk</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-500">
                      {insiderSummary.total_users - insiderSummary.suspicious_users}
                    </div>
                    <div className="text-sm text-muted-foreground">Low Risk</div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-foreground">Risk Distribution</h4>
                  {insiderSummary.risk_distribution && Object.keys(insiderSummary.risk_distribution).length > 0 ? (
                    Object.entries(insiderSummary.risk_distribution).map(([level, count]) => (
                      <div key={level} className="flex items-center justify-between">
                        <span className={`text-sm font-medium ${getRiskLevelColor(level)}`}>
                          {level.charAt(0).toUpperCase() + level.slice(1)}
                        </span>
                        <Badge variant="outline">{count}</Badge>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-muted-foreground">No risk distribution data available</div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-blue-500" />
                  Activity Types
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {insiderSummary.activities_by_type && Object.keys(insiderSummary.activities_by_type).length > 0 ? (
                    Object.entries(insiderSummary.activities_by_type).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground capitalize">
                          {type.replace('_', ' ')}
                        </span>
                        <Badge variant="outline">{count}</Badge>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-muted-foreground">No activity data available</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Top Threats */}
        {insiderSummary && (
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-destructive" />
                Top Threat Users
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {insiderSummary.top_threats && insiderSummary.top_threats.length > 0 ? (
                  insiderSummary.top_threats.map((threat, index) => (
                    <div key={threat.user_id} className="flex items-center justify-between p-3 rounded-lg bg-background border border-border">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                          {index + 1}
                        </div>
                        <div>
                          <div className="font-medium text-foreground">{threat.username}</div>
                          <div className="text-sm text-muted-foreground">User ID: {threat.user_id}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{threat.threat_count} threats</Badge>
                        <Badge className={getSeverityColor(threat.risk_level)}>
                          {threat.risk_level.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">No threat data available</div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {error && (
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                {error}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  )
}
