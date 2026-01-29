"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertCircle, TrendingUp, RefreshCw, CheckCircle, XCircle, Calendar as CalendarIcon, Filter, Download, Trash2, FileSearch, ExternalLink } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { config } from "@/lib/config"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

interface PcapDetectionItem {
  id: string
  title: string
  severity: "low" | "medium" | "high" | "critical"
  description?: string
  ml_source?: string
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

export default function AlertsPage() {
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
  const [filters, setFilters] = useState({
    severity: "all",
    type: "all",
    resolved: "all"
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalAlerts, setTotalAlerts] = useState(0)

  // Detections from latest PCAP analysis
  const [pcapDetections, setPcapDetections] = useState<PcapDetectionItem[]>([])
  const [pcapLoading, setPcapLoading] = useState(true)

  const fetchLatestPcapDetections = useCallback(async () => {
    setPcapLoading(true)
    try {
      const data = await flaskApi.getLastPcapAnalysis()
      if (data && !("error" in data) && Array.isArray(data.detections)) {
        setPcapDetections(
          (data.detections as { id?: string; title?: string; severity?: string; description?: string; ml_source?: string }[]).map(
            (d, i) => ({
              id: d.id ?? `pcap-${i}`,
              title: d.title ?? "Detection",
              severity: (d.severity as PcapDetectionItem["severity"]) ?? "low",
              description: d.description,
              ml_source: d.ml_source,
            })
          )
        )
      } else {
        setPcapDetections([])
      }
    } catch {
      setPcapDetections([])
    } finally {
      setPcapLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLatestPcapDetections()
  }, [fetchLatestPcapDetections])

  const fetchAlertsData = async (page = 1) => {
    try {
      setError(null)
      setLoading(true)
      
      // Build query parameters
      const params: any = {
        limit: 50,
        page: page
      }
      
      if (dateRange.from) {
        params.start_date = dateRange.from.toISOString()
      }
      if (dateRange.to) {
        params.end_date = dateRange.to.toISOString()
      }
      if (filters.severity !== "all") {
        params.severity = filters.severity
      }
      if (filters.type !== "all") {
        params.type = filters.type
      }
      if (filters.resolved !== "all") {
        params.resolved = filters.resolved === "resolved"
      }
      
      const response = await flaskApi.getAlerts(params)
      
      // Transform Flask alerts to include resolved status
      const transformedAlerts = response.alerts.map(alert => ({
        id: alert.id.toString(),
        timestamp: alert.timestamp,
        sourceIp: alert.source_ip,
        destIp: alert.dest_ip,
        protocol: alert.protocol,
        type: alert.type,
        severity: alert.severity,
        description: alert.description,
        resolved: alert.resolved || false,
        confidenceScore: alert.confidence_score,
        classificationResult: alert.classification_result
      }))
      
      setAlerts(transformedAlerts)
      setTotalAlerts(response.total)
      setTotalPages(Math.ceil(response.total / 50))
      setCurrentPage(page)
    } catch (err) {
      console.error('Error fetching alerts:', err)
      setError('Failed to fetch alerts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlertsData(1)
  }, [filters, dateRange])

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

  const handleDeleteAlert = async (alertId: string) => {
    setUpdatingAlerts(prev => new Set(prev).add(alertId))
    try {
      await flaskApi.deleteAlert(parseInt(alertId))
      
      // Remove from local state
      setAlerts(prev => prev.filter(alert => alert.id !== alertId))
      
      // Remove from selection if selected
      setSelectedAlerts(prev => {
        const newSet = new Set(prev)
        newSet.delete(alertId)
        return newSet
      })
    } catch (error) {
      console.error('Error deleting alert:', error)
      setError('Failed to delete alert')
    } finally {
      setUpdatingAlerts(prev => {
        const newSet = new Set(prev)
        newSet.delete(alertId)
        return newSet
      })
    }
  }

  const handleBulkDelete = async () => {
    if (selectedAlerts.size === 0) return
    
    setUpdatingAlerts(prev => new Set([...prev, ...selectedAlerts]))
    try {
      // Use bulk delete endpoint
      const alertIds = Array.from(selectedAlerts)
      const result = await flaskApi.bulkDeleteAlerts({ alert_ids: alertIds })
      
      if (result.failed_count > 0) {
        console.warn(`Failed to delete ${result.failed_count} alerts:`, result.failed_alerts)
      }
      
      // Remove from local state
      setAlerts(prev => prev.filter(alert => !selectedAlerts.has(alert.id)))
      
      // Clear selection
      setSelectedAlerts(new Set())
    } catch (error) {
      console.error('Error bulk deleting alerts:', error)
      setError('Failed to bulk delete alerts')
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

  const getPcapSeverityVariant = (severity: string): "destructive" | "secondary" | "default" | "outline" => {
    if (severity === "critical" || severity === "high") return "destructive"
    if (severity === "medium") return "default"
    return "secondary"
  }

  const handleExportAlerts = () => {
    const csvContent = [
      ['ID', 'Timestamp', 'Source IP', 'Dest IP', 'Protocol', 'Type', 'Severity', 'Description', 'Resolved'],
      ...alerts.map(alert => [
        alert.id,
        alert.timestamp,
        alert.sourceIp,
        alert.destIp,
        alert.protocol,
        alert.type,
        alert.severity,
        alert.description,
        alert.resolved ? 'Yes' : 'No'
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alerts-${format(new Date(), 'yyyy-MM-dd')}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Security Alerts</h1>
            <p className="text-muted-foreground mt-2">Comprehensive alert management and historical analysis</p>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleExportAlerts} variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
            <Button onClick={() => fetchAlertsData(currentPage)} disabled={loading} variant="outline" size="sm">
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
          </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {/* Date Range Picker */}
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

              {/* Severity Filter */}
              <Select value={filters.severity} onValueChange={(value) => setFilters(prev => ({ ...prev, severity: value }))}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severities</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>

              {/* Type Filter */}
              <Select value={filters.type} onValueChange={(value) => setFilters(prev => ({ ...prev, type: value }))}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="signature">Signature</SelectItem>
                  <SelectItem value="anomaly">Anomaly</SelectItem>
                  <SelectItem value="classification">Classification</SelectItem>
                </SelectContent>
              </Select>

              {/* Resolved Filter */}
              <Select value={filters.resolved} onValueChange={(value) => setFilters(prev => ({ ...prev, resolved: value }))}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="unresolved">Unresolved</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                </SelectContent>
              </Select>

              {/* Clear Filters */}
              <Button
                variant="ghost"
                onClick={() => {
                  setDateRange({ from: undefined, to: undefined })
                  setFilters({ severity: "all", type: "all", resolved: "all" })
                }}
              >
                Clear All
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Detections from PCAP */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileSearch className="h-5 w-5" />
              Detections from PCAP
              {pcapLoading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pcapLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : pcapDetections.length === 0 ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-muted-foreground">No PCAP detections. Upload and analyze a PCAP to see findings here.</p>
                <Button asChild variant="outline" size="sm" className="w-fit">
                  <Link href="/analysis" className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" />
                    Go to Analysis
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {pcapDetections.map((d) => (
                  <div
                    key={d.id}
                    className="flex items-start gap-3 p-3 rounded-lg bg-background border border-border"
                  >
                    <Badge variant={getPcapSeverityVariant(d.severity)} className="shrink-0">
                      {d.severity.toUpperCase()}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{d.title}</p>
                      {d.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{d.description}</p>
                      )}
                      {d.ml_source && (
                        <span className="text-xs text-muted-foreground mt-1 inline-block">Source: {d.ml_source}</span>
                      )}
                    </div>
                  </div>
                ))}
                <Button asChild variant="ghost" size="sm" className="mt-2 w-fit">
                  <Link href="/analysis" className="flex items-center gap-2 text-muted-foreground">
                    <ExternalLink className="h-4 w-4" />
                    View full PCAP analysis
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Alerts Table */}
        <Card className="bg-card border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              Alerts ({totalAlerts})
              {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
            </CardTitle>
            <div className="flex items-center gap-2">
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
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={handleBulkDelete}
                    disabled={updatingAlerts.size > 0}
                    className="text-xs"
                  >
                    <Trash2 className="h-3 w-3 mr-1" />
                    Delete ({selectedAlerts.size})
                  </Button>
                </div>
              )}
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
                Select all ({selectedAlerts.size}/{alerts.length})
              </span>
            </div>
            
            <div className="space-y-3">
              {alerts.map((alert) => (
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
                        <span>{format(new Date(alert.timestamp), 'MMM dd, yyyy HH:mm:ss')}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
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
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteAlert(alert.id)}
                        disabled={updatingAlerts.has(alert.id)}
                        className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                <div className="text-sm text-muted-foreground">
                  Showing {((currentPage - 1) * 50) + 1} to {Math.min(currentPage * 50, totalAlerts)} of {totalAlerts} alerts
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchAlertsData(currentPage - 1)}
                    disabled={currentPage === 1 || loading}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchAlertsData(currentPage + 1)}
                    disabled={currentPage === totalPages || loading}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}