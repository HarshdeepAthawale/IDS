"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { AlertTriangle, User, Calendar as CalendarIcon, ArrowLeft, Activity, Shield, Clock } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

interface UserActivity {
  id: number
  user_id: string
  username: string
  activity_type: 'login' | 'file_access' | 'network_access' | 'privilege_escalation' | 'data_exfiltration' | 'suspicious_command' | 'off_hours_access'
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  source_ip: string | null
  destination: string | null
  command: string | null
  file_size: number | null
  success: boolean | null
  timestamp: string
  session_id: string | null
  user_agent: string | null
  geolocation: string | null
}

interface UserSummary {
  user_id: string
  username: string
  total_activities: number
  high_severity_count: number
  critical_severity_count: number
  most_common_activity: string
  last_activity: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
}

export default function UserDetailPage() {
  const params = useParams()
  const userId = params.userId as string
  
  const [userSummary, setUserSummary] = useState<UserSummary | null>(null)
  const [activities, setActivities] = useState<UserActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<{ from: Date | undefined; to: Date | undefined }>({
    from: undefined,
    to: undefined
  })
  const [showDatePicker, setShowDatePicker] = useState(false)

  const fetchUserData = async () => {
    try {
      setError(null)
      setLoading(true)
      
      // Build query parameters
      const params: any = {
        user_id: userId,
        limit: 100
      }
      
      if (dateRange.from) {
        params.start_date = dateRange.from.toISOString()
      }
      if (dateRange.to) {
        params.end_date = dateRange.to.toISOString()
      }
      
      const response = await flaskApi.getInsiderThreats(params)
      
      setActivities(response.activities || [])
      
      // Create user summary from activities
      if (response.activities && response.activities.length > 0) {
        const firstActivity = response.activities[0]
        const activityCounts = response.activities.reduce((acc: any, activity: UserActivity) => {
          acc[activity.activity_type] = (acc[activity.activity_type] || 0) + 1
          return acc
        }, {})
        
        const mostCommon = Object.keys(activityCounts).reduce((a, b) => 
          activityCounts[a] > activityCounts[b] ? a : b
        )
        
        const highSeverityCount = response.activities.filter((a: UserActivity) => a.severity === 'high').length
        const criticalSeverityCount = response.activities.filter((a: UserActivity) => a.severity === 'critical').length
        
        setUserSummary({
          user_id: firstActivity.user_id,
          username: firstActivity.username,
          total_activities: response.activities.length,
          high_severity_count: highSeverityCount,
          critical_severity_count: criticalSeverityCount,
          most_common_activity: mostCommon,
          last_activity: response.activities[0].timestamp,
          risk_score: (highSeverityCount * 0.3 + criticalSeverityCount * 0.7) / response.activities.length,
          risk_level: criticalSeverityCount > 0 ? 'critical' : highSeverityCount > 2 ? 'high' : 'medium'
        })
      }
    } catch (err) {
      console.error('Error fetching user data:', err)
      setError('Failed to fetch user activity data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId) {
      fetchUserData()
    }
  }, [userId, dateRange])

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

  const getActivityIcon = (activityType: string) => {
    switch (activityType) {
      case "data_exfiltration":
        return <Shield className="h-4 w-4" />
      case "off_hours_access":
        return <Clock className="h-4 w-4" />
      case "privilege_escalation":
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <Activity className="h-4 w-4" />
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
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <User className="h-8 w-8" />
              User Activity Details
            </h1>
            <p className="text-muted-foreground mt-2">Detailed analysis of user activities and threat patterns</p>
          </div>
        </div>

        {/* User Summary */}
        {userSummary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <User className="h-5 w-5 text-blue-500" />
                  User Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Username</span>
                  <Badge variant="outline">{userSummary.username}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">User ID</span>
                  <Badge variant="outline">{userSummary.user_id}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Last Activity</span>
                  <Badge variant="outline">{format(new Date(userSummary.last_activity), 'MMM dd, HH:mm')}</Badge>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Activity className="h-5 w-5 text-green-500" />
                  Activity Stats
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Total Activities</span>
                  <Badge variant="outline">{userSummary.total_activities}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">High Severity</span>
                  <Badge variant="outline">{userSummary.high_severity_count}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Critical Severity</span>
                  <Badge variant="outline">{userSummary.critical_severity_count}</Badge>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  Risk Assessment
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Risk Level</span>
                  <Badge variant="outline" className={getRiskLevelColor(userSummary.risk_level)}>
                    {userSummary.risk_level.toUpperCase()}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Risk Score</span>
                  <Badge variant="outline">{(userSummary.risk_score * 100).toFixed(1)}%</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Most Common</span>
                  <Badge variant="outline">{userSummary.most_common_activity}</Badge>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <CalendarIcon className="h-5 w-5 text-purple-500" />
                  Timeline
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">First Activity</span>
                  <Badge variant="outline">
                    {activities.length > 0 ? format(new Date(activities[activities.length - 1].timestamp), 'MMM dd') : 'N/A'}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Last Activity</span>
                  <Badge variant="outline">
                    {activities.length > 0 ? format(new Date(activities[0].timestamp), 'MMM dd') : 'N/A'}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Activity Span</span>
                  <Badge variant="outline">
                    {activities.length > 1 ? 
                      `${Math.ceil((new Date(activities[0].timestamp).getTime() - new Date(activities[activities.length - 1].timestamp).getTime()) / (1000 * 60 * 60 * 24))} days` : 
                      '1 day'
                    }
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Date Filter */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Filter by Date Range
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Popover open={showDatePicker} onOpenChange={setShowDatePicker}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "justify-start text-left font-normal",
                      !dateRange.from && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {dateRange.from ? (
                      dateRange.to ? (
                        <>
                          {format(dateRange.from, "LLL dd")} -{" "}
                          {format(dateRange.to, "LLL dd, y")}
                        </>
                      ) : (
                        format(dateRange.from, "LLL dd, y")
                      )
                    ) : (
                      <span>Pick date range</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    initialFocus
                    mode="range"
                    defaultMonth={dateRange.from}
                    selected={dateRange}
                    onSelect={(range) => {
                      setDateRange({
                        from: range?.from,
                        to: range?.to
                      })
                      if (range?.from && range?.to) {
                        setShowDatePicker(false)
                      }
                    }}
                    numberOfMonths={2}
                  />
                </PopoverContent>
              </Popover>

              {(dateRange.from || dateRange.to) && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setDateRange({ from: undefined, to: undefined })
                  }}
                >
                  Clear Filter
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Activity Timeline */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Activity Timeline ({activities.length} activities)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activities.map((activity, index) => (
                <div key={activity.id} className="flex items-start gap-4 p-4 rounded-lg bg-background border border-border">
                  <div className="flex-shrink-0 mt-1">
                    {getActivityIcon(activity.activity_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-sm font-semibold px-2 py-1 rounded ${getSeverityColor(activity.severity)}`}>
                        {activity.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-muted-foreground">{activity.activity_type}</span>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(activity.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-foreground mb-2">{activity.description}</p>
                    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                      {activity.source_ip && <span>Source: {activity.source_ip}</span>}
                      {activity.destination && <span>Destination: {activity.destination}</span>}
                      {activity.file_size && <span>Size: {(activity.file_size / 1024 / 1024).toFixed(2)} MB</span>}
                      {activity.success !== null && (
                        <span className={activity.success ? "text-green-500" : "text-red-500"}>
                          {activity.success ? "Success" : "Failed"}
                        </span>
                      )}
                      {activity.geolocation && <span>Location: {activity.geolocation}</span>}
                    </div>
                    {activity.command && (
                      <div className="mt-2 p-2 bg-muted rounded text-xs font-mono">
                        Command: {activity.command}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}
