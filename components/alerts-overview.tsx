"use client"

import { useState, useEffect, useCallback, useMemo, memo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { AlertCircle, TrendingUp, RefreshCw, CheckCircle, XCircle, MoreHorizontal, Calendar as CalendarIcon, Filter } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { useWebSocket } from "@/hooks/use-websocket"

/** Raw alert shape from Flask API */
interface ApiAlert {
  id: number | string
  timestamp: string
  source_ip: string
  dest_ip: string
  protocol: string
  type: "signature" | "anomaly" | "classification"
  severity: "critical" | "high" | "medium" | "low"
  description: string
  resolved?: boolean
  confidence_score?: number
  classification_result?: {
    label: string
    confidence: number
    probabilities?: { benign: number; malicious: number }
  }
}

interface Alert {
  id: string
  timestamp: string
  sourceIp: string
  destIp: string
  protocol: string
  type: "signature" | "anomaly" | "classification"
  severity: "critical" | "high" | "medium" | "low"
  description: string
  resolved?: boolean
  confidenceScore?: number
  classificationResult?: {
    label: string
    confidence: number
    probabilities?: {
      benign: number
      malicious: number
    }
  }
}

function AlertsOverview() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set())
  const [updatingAlerts, setUpdatingAlerts] = useState<Set<string>>(new Set())
  const [dateRange, setDateRange] = useState<{ from: Date | undefined; to: Date | undefined }>({
    from: undefined,
    to: undefined
  })
  const [showDatePicker, setShowDatePicker] = useState(false)
  
  // Real-time WebSocket connection
  const { isConnected, on, off } = useWebSocket({ room: 'dashboard' })

  const fetchAlertsData = useCallback(async () => {
    try {
      setError(null)
      
      // Build query parameters
      const params: any = {}
      if (dateRange.from) {
        params.start_date = dateRange.from.toISOString()
      }
      if (dateRange.to) {
        params.end_date = dateRange.to.toISOString()
      }
      
      const response = await flaskApi.getAlerts(params)
      // Transform Flask alerts to include resolved status
      const transformedAlerts = (response.alerts as ApiAlert[]).map(alert => ({
        id: alert.id.toString(),
        timestamp: alert.timestamp,
        sourceIp: alert.source_ip,
        destIp: alert.dest_ip,
        protocol: alert.protocol,
        type: alert.type,
        severity: alert.severity,
        description: alert.description,
        resolved: alert.resolved ?? false,
        confidenceScore: alert.confidence_score,
        classificationResult: alert.classification_result
      }))
      setAlerts(transformedAlerts)
    } catch (err) {
      console.error('Error fetching alerts:', err)
      setError('Failed to fetch real-time alerts')
    } finally {
      setLoading(false)
    }
  }, [dateRange.from, dateRange.to])

  // Initial fetch
  useEffect(() => {
    fetchAlertsData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange.from, dateRange.to]) // Only refetch when date range changes

  // Real-time WebSocket updates
  useEffect(() => {
    if (!isConnected) {
      // Only use polling as true fallback when WebSocket is disconnected
      const fallbackInterval = setInterval(() => {
        fetchAlertsData()
      }, 5000)
      return () => clearInterval(fallbackInterval)
    }

    // Listen for new alerts in real-time (no debounce for critical alerts)
    const handleNewAlert = (data: any) => {
      const alertData = data.data || data
      const newAlert: Alert = {
        id: alertData.alert_id || alertData.id || Date.now().toString(),
        timestamp: alertData.timestamp || new Date().toISOString(),
        sourceIp: alertData.source_ip || 'Unknown',
        destIp: alertData.dest_ip || 'Unknown',
        protocol: alertData.protocol || 'Unknown',
        type: alertData.type || alertData.alert_type || 'anomaly',
        severity: alertData.severity || 'medium',
        description: alertData.description || 'New threat detected',
        resolved: false,
        confidenceScore: alertData.confidence_score,
        classificationResult: alertData.classification_result
      }
      
      // Only add if not in date range filter or matches filter
      setAlerts(prev => {
        // Check if alert already exists
        const exists = prev.find(a => a.id === newAlert.id)
        if (exists) return prev
        
        // If date range is set, check if alert matches
        if (dateRange.from || dateRange.to) {
          const alertDate = new Date(newAlert.timestamp)
          if (dateRange.from && alertDate < dateRange.from) return prev
          if (dateRange.to && alertDate > dateRange.to) return prev
        }
        
        return [newAlert, ...prev]
      })
    }

    // Listen for alert updates (resolved/unresolved)
    const handleAlertUpdate = (data: any) => {
      const updateData = data.data || data
      if (updateData.alert_id) {
        setAlerts(prev => prev.map(alert => 
          alert.id === updateData.alert_id.toString() 
            ? { ...alert, resolved: updateData.resolved ?? alert.resolved }
            : alert
        ))
      }
    }

    on('new_alert', handleNewAlert)
    on('alert_updated', handleAlertUpdate)

    return () => {
      off('new_alert', handleNewAlert)
      off('alert_updated', handleAlertUpdate)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected, dateRange.from, dateRange.to]) // on/off are stable from context

  // Alert management functions
  const handleAlertUpdate = async (alertId: string, resolved: boolean) => {
    setUpdatingAlerts(prev => new Set(prev).add(alertId))
    try {
      await flaskApi.updateAlert(parseInt(alertId), { 
        resolved, 
        resolved_by: 'admin' 
      })
      
      // Update local state
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId ? { ...alert, resolved } : alert
      ))
    } catch (error) {
      console.error('Error updating alert:', error)
      setError('Failed to update alert')
    } finally {
      setUpdatingAlerts(prev => {
        const newSet = new Set(prev)
        newSet.delete(alertId)
        return newSet
      })
    }
  }

  const handleBulkResolve = async (resolved: boolean) => {
    if (selectedAlerts.size === 0) return
    
    setUpdatingAlerts(prev => new Set([...prev, ...selectedAlerts]))
    try {
      await flaskApi.bulkResolveAlerts({
        alert_ids: Array.from(selectedAlerts).map(id => parseInt(id)),
        resolved,
        resolved_by: 'admin'
      })
      
      // Update local state
      setAlerts(prev => prev.map(alert => 
        selectedAlerts.has(alert.id) ? { ...alert, resolved } : alert
      ))
      
      // Clear selection
      setSelectedAlerts(new Set())
    } catch (error) {
      console.error('Error bulk updating alerts:', error)
      setError('Failed to bulk update alerts')
    } finally {
      setUpdatingAlerts(prev => {
        const newSet = new Set(prev)
        selectedAlerts.forEach(id => newSet.delete(id))
        return newSet
      })
    }
  }

  const handleSelectAlert = (alertId: string, checked: boolean) => {
    setSelectedAlerts(prev => {
      const newSet = new Set(prev)
      if (checked) {
        newSet.add(alertId)
      } else {
        newSet.delete(alertId)
      }
      return newSet
    })
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedAlerts(new Set(alerts.map(alert => alert.id)))
    } else {
      setSelectedAlerts(new Set())
    }
  }

  const getSeverityColor = useCallback((severity: string) => {
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
  }, [])

  // Memoize expensive computations
  const sortedAlerts = useMemo(() => {
    return [...alerts].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  }, [alerts])

  const selectedAlertsCount = useMemo(() => selectedAlerts.size, [selectedAlerts])

  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-destructive" />
          Recent Alerts
          {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
        </CardTitle>
        <div className="flex items-center gap-2">
          {/* Date Range Picker */}
          <Popover open={showDatePicker} onOpenChange={setShowDatePicker}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className={cn(
                  "text-xs justify-start text-left font-normal",
                  !dateRange.from && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-3 w-3" />
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
                  setDateRange(
                    range
                      ? { from: range.from, to: range.to ?? undefined }
                      : { from: undefined, to: undefined }
                  )
                  if (range?.from && range?.to) {
                    setShowDatePicker(false)
                    fetchAlertsData()
                  }
                }}
                numberOfMonths={2}
              />
            </PopoverContent>
          </Popover>
          
          {/* Clear Date Filter */}
          {(dateRange.from || dateRange.to) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDateRange({ from: undefined, to: undefined })
                fetchAlertsData()
              }}
              className="text-xs"
            >
              Clear
            </Button>
          )}
          
          {selectedAlerts.size > 0 && (
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkResolve(true)}
                disabled={updatingAlerts.size > 0}
                className="text-xs"
              >
                <CheckCircle className="h-3 w-3 mr-1" />
                Resolve ({selectedAlerts.size})
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkResolve(false)}
                disabled={updatingAlerts.size > 0}
                className="text-xs"
              >
                <XCircle className="h-3 w-3 mr-1" />
                Unresolve ({selectedAlerts.size})
              </Button>
            </div>
          )}
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
          <button
            onClick={fetchAlertsData}
            disabled={loading}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Bulk selection header */}
        <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border">
          <Checkbox
            checked={selectedAlerts.size === alerts.length && alerts.length > 0}
            onCheckedChange={handleSelectAll}
            className="data-[state=checked]:bg-primary"
          />
          <span className="text-xs text-muted-foreground">
            Select all ({selectedAlertsCount}/{alerts.length})
          </span>
        </div>
        
        <div className="space-y-3">
          {sortedAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`flex items-start justify-between p-3 rounded-lg bg-background border transition-colors ${
                alert.resolved 
                  ? 'border-green-200 bg-green-50/10 opacity-75' 
                  : 'border-border hover:border-primary'
              }`}
            >
              <div className="flex items-start gap-3 flex-1">
                <Checkbox
                  checked={selectedAlerts.has(alert.id)}
                  onCheckedChange={(checked) => handleSelectAlert(alert.id, checked as boolean)}
                  className="mt-1 data-[state=checked]:bg-primary"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-sm font-semibold ${getSeverityColor(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-xs text-muted-foreground">{alert.type}</span>
                    {alert.resolved && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        RESOLVED
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-foreground">{alert.description}</p>
                  {alert.classificationResult && (
                    <div className="mt-2 p-2 rounded bg-blue-500/10 border border-blue-500/20">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-semibold text-blue-500">ML Classification:</span>
                        <span className="text-foreground">{alert.classificationResult.label}</span>
                        <span className="text-muted-foreground">
                          (Confidence: {(alert.classificationResult.confidence * 100).toFixed(1)}%)
                        </span>
                        {alert.classificationResult.probabilities && (
                          <span className="text-muted-foreground">
                            | Benign: {(alert.classificationResult.probabilities.benign * 100).toFixed(1)}% 
                            | Malicious: {(alert.classificationResult.probabilities.malicious * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  {alert.confidenceScore && !alert.classificationResult && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      Confidence: {(alert.confidenceScore * 100).toFixed(1)}%
                    </div>
                  )}
                  <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                    <span>From: {alert.sourceIp}</span>
                    <span>To: {alert.destIp}</span>
                    <span>{alert.protocol}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <div className="text-xs text-muted-foreground whitespace-nowrap">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAlertUpdate(alert.id, !alert.resolved)}
                    disabled={updatingAlerts.has(alert.id)}
                    className="h-6 w-6 p-0"
                  >
                    {alert.resolved ? (
                      <XCircle className="h-3 w-3 text-orange-500" />
                    ) : (
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default memo(AlertsOverview)
