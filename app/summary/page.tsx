"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Activity, TrendingUp, RefreshCw, Shield, FileSearch, ExternalLink, X, CheckCircle } from "lucide-react"
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

interface PcapDetection {
  id: string
  title: string
  severity?: "low" | "medium" | "high" | "critical"
  confidence?: number
  description?: string
  evidence?: Record<string, unknown>
  mitre?: { technique?: string; tactic?: string }
  ml_source?: "signature" | "anomaly" | "classification"
}

interface LatestPcapSummary {
  metadata?: {
    packets_processed?: number
    bytes_processed?: number
    processing_time_ms?: number
    duration_seconds?: number
    filename?: string
    model_info?: {
      ml_enabled?: boolean
      anomaly_detector?: { enabled?: boolean; trained?: boolean }
      classification_detector?: { enabled?: boolean; trained?: boolean }
      detection_counts?: { signature?: number; anomaly?: number; classification?: number }
      average_confidence?: number
    }
  }
  risk?: { score?: number; level?: string; rationale?: string[] }
  detections?: PcapDetection[]
  summary?: {
    top_protocols?: { name: string; count: number; percentage?: number }[]
    top_talkers?: { ip: string; packets: number }[]
    top_ports?: { port: number; packets: number }[]
    dns_queries?: string[]
    tls_handshakes?: { server: string; port: number }[]
    http_hosts?: string[]
    flow_samples?: { src: string; dst: string; proto: string; dport: number; packets: number }[]
  }
  evidence?: {
    timeline?: { bucket: string; packets: number; bytes: number }[]
    endpoint_matrix?: { src: string; dst: string; packets: number }[]
  }
}

function formatBytes(bytes?: number) {
  if (!bytes && bytes !== 0) return "N/A"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDuration(seconds?: number) {
  if (!seconds && seconds !== 0) return "N/A"
  if (seconds < 60) return `${Math.round(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${minutes}m ${secs}s`
}

function getThreatColor(level: string) {
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

export default function SummaryPage() {
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null)
  const [pcapLatest, setPcapLatest] = useState<LatestPcapSummary | null>(null)
  const [pcapLoading, setPcapLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showFullPcapAnalysis, setShowFullPcapAnalysis] = useState(false)
  const fullPcapSectionRef = useRef<HTMLDivElement>(null)

  const [pcapStats, setPcapStats] = useState<{ total_detections: number; critical_detections: number } | null>(null)

  const openFullPcapAnalysis = useCallback(() => {
    setShowFullPcapAnalysis(true)
    setTimeout(() => fullPcapSectionRef.current?.scrollIntoView({ behavior: "smooth" }), 100)
  }, [])

  const fetchSummaryData = async () => {
    try {
      setError(null)
      setLoading(true)
      const [alertData, stats] = await Promise.all([
        flaskApi.getAlertSummary(),
        flaskApi.getPcapStats().catch(() => ({ total_detections: 0, critical_detections: 0 })),
      ])
      setAlertSummary(alertData as unknown as AlertSummary)
      setPcapStats(stats)
    } catch (err) {
      console.error('Error fetching summary data:', err)
      setError('Failed to fetch summary data')
    } finally {
      setLoading(false)
    }
  }

  const fetchLatestPcap = useCallback(async () => {
    setPcapLoading(true)
    try {
      const data = await flaskApi.getLastPcapAnalysis()
      if (data && !("error" in data)) {
        setPcapLatest(data as LatestPcapSummary)
      } else {
        setPcapLatest(null)
      }
    } catch {
      setPcapLatest(null)
    } finally {
      setPcapLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSummaryData()
  }, [])

  useEffect(() => {
    fetchLatestPcap()
  }, [fetchLatestPcap])

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
                  {(alertSummary.total_alerts ?? alertSummary.total_recent_alerts ?? 0) + (pcapStats?.total_detections ?? 0)}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {alertSummary.unresolved_alerts} unresolved
                  {(pcapStats?.total_detections ?? 0) > 0 && (
                    <span> · {(pcapStats?.total_detections ?? 0)} from PCAP</span>
                  )}
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
                  {(alertSummary.alerts_by_severity?.critical || 0) + (pcapStats?.critical_detections ?? 0)}
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

        {/* Latest PCAP Analysis */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileSearch className="h-4 w-4" />
              Latest PCAP Analysis
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={fetchLatestPcap}
                disabled={pcapLoading}
              >
                <RefreshCw className={`h-4 w-4 ${pcapLoading ? 'animate-spin' : ''}`} />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pcapLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : !pcapLatest ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-muted-foreground">No PCAP analysis yet.</p>
                <Button asChild variant="outline" size="sm" className="w-fit">
                  <Link href="/analysis" className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" />
                    Upload and analyze a PCAP
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <span className="text-xs text-muted-foreground">Risk</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-lg font-semibold">{pcapLatest.risk?.score ?? "--"}</span>
                    <Badge variant={pcapLatest.risk?.level === "high" || pcapLatest.risk?.level === "critical" ? "destructive" : "secondary"}>
                      {(pcapLatest.risk?.level ?? "low").toUpperCase()}
                    </Badge>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Packets</span>
                  <div className="text-lg font-semibold mt-0.5">{pcapLatest.metadata?.packets_processed ?? "--"}</div>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Detections</span>
                  <div className="text-lg font-semibold mt-0.5">{pcapLatest.detections?.length ?? 0}</div>
                </div>
                {pcapLatest.metadata?.filename && (
                  <p className="text-xs text-muted-foreground truncate max-w-[180px]" title={pcapLatest.metadata.filename}>
                    {pcapLatest.metadata.filename}
                  </p>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="ml-auto"
                  onClick={openFullPcapAnalysis}
                >
                  <ExternalLink className="h-4 w-4" />
                  View full analysis
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Full PCAP Analysis (expanded when "View full analysis" is clicked) */}
        {showFullPcapAnalysis && pcapLatest && (
          <div ref={fullPcapSectionRef} className="space-y-6">
            <Card className="bg-card border-border border-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    Full PCAP Analysis
                    {pcapLatest.metadata?.filename && (
                      <span className="text-xs font-normal text-muted-foreground">({pcapLatest.metadata.filename})</span>
                    )}
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowFullPcapAnalysis(false)}
                    className="gap-2"
                  >
                    <X className="h-4 w-4" />
                    Hide full analysis
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="p-3 rounded-lg border border-border bg-background">
                    <div className="text-xs text-muted-foreground mb-1">Risk Score</div>
                    <div className="flex items-center gap-2">
                      <div className="text-2xl font-bold">{pcapLatest.risk?.score ?? "--"}</div>
                      <Badge className={getThreatColor(pcapLatest.risk?.level || "low")}>
                        {(pcapLatest.risk?.level || "low").toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-background">
                    <div className="text-xs text-muted-foreground mb-1">Total Packets</div>
                    <div className="text-2xl font-bold">{pcapLatest.metadata?.packets_processed ?? "--"}</div>
                    <div className="text-xs text-muted-foreground">{formatBytes(pcapLatest.metadata?.bytes_processed)}</div>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-background">
                    <div className="text-xs text-muted-foreground mb-1">Duration</div>
                    <div className="text-2xl font-bold">{formatDuration(pcapLatest.metadata?.duration_seconds)}</div>
                    <div className="text-xs text-muted-foreground">{pcapLatest.metadata?.processing_time_ms}ms</div>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-background">
                    <div className="text-xs text-muted-foreground mb-1">Detections</div>
                    <div className="text-2xl font-bold">{pcapLatest.detections?.length ?? 0}</div>
                    <div className="text-xs text-muted-foreground">
                      {pcapLatest.metadata?.model_info?.detection_counts ? (
                        <>
                          ML: {(pcapLatest.metadata.model_info.detection_counts.anomaly ?? 0) + (pcapLatest.metadata.model_info.detection_counts.classification ?? 0)} |
                          Heuristic: {pcapLatest.metadata.model_info.detection_counts.signature ?? 0}
                          {!pcapLatest.metadata?.model_info?.ml_enabled && (
                            <span className="block mt-0.5 text-muted-foreground/80">Traditional rules only · ML planned</span>
                          )}
                        </>
                      ) : (
                        "Traditional heuristics"
                      )}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-background">
                    <div className="text-xs text-muted-foreground mb-1">ML Models</div>
                    <div className="space-y-1">
                      {pcapLatest.metadata?.model_info?.ml_enabled ? (
                        <>
                          <div className="flex items-center gap-1 text-xs">
                            <Badge variant={pcapLatest.metadata.model_info.anomaly_detector?.trained ? "default" : "secondary"} className="text-[10px]">
                              Anomaly {pcapLatest.metadata.model_info.anomaly_detector?.trained ? "✓" : "✗"}
                            </Badge>
                          </div>
                          {pcapLatest.metadata?.model_info.classification_detector?.enabled && (
                            <div className="flex items-center gap-1 text-xs">
                              <Badge variant={pcapLatest.metadata.model_info.classification_detector?.trained ? "default" : "secondary"} className="text-[10px]">
                                Classify {pcapLatest.metadata.model_info.classification_detector?.trained ? "✓" : "✗"}
                              </Badge>
                            </div>
                          )}
                          {pcapLatest.metadata?.model_info.average_confidence != null && (
                            <div className="text-xs text-muted-foreground">
                              Avg Confidence: {(pcapLatest.metadata.model_info.average_confidence * 100).toFixed(1)}%
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-xs text-muted-foreground">Traditional only · ML integration planned</div>
                      )}
                    </div>
                  </div>
                </div>

                {pcapLatest.risk?.rationale && pcapLatest.risk.rationale.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-foreground">Risk rationale</h3>
                    <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                      {pcapLatest.risk.rationale.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-foreground">Top Protocols</h3>
                    <div className="flex flex-wrap gap-2">
                      {(pcapLatest.summary?.top_protocols || []).map((proto) => (
                        <Badge key={proto.name} variant="secondary" className="text-xs">
                          {proto.name}: {proto.percentage != null ? `${proto.percentage}%` : proto.count}
                        </Badge>
                      ))}
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">Top Talkers</h3>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      {(pcapLatest.summary?.top_talkers || []).map((talker) => (
                        <div key={talker.ip} className="flex items-center gap-2">
                          <span className="font-mono">{talker.ip}</span>
                          <span className="text-foreground font-medium">{talker.packets} pkts</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-foreground">Top Ports</h3>
                    <div className="flex flex-wrap gap-2">
                      {(pcapLatest.summary?.top_ports || []).map((port) => (
                        <Badge key={port.port} variant="outline" className="text-xs">
                          {port.port} ({port.packets} pkts)
                        </Badge>
                      ))}
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">DNS / TLS / HTTP</h3>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>DNS: {(pcapLatest.summary?.dns_queries || []).slice(0, 5).join(", ") || "—"}</div>
                      <div>TLS: {(pcapLatest.summary?.tls_handshakes || []).slice(0, 3).map((t) => t.server).join(", ") || "—"}</div>
                      <div>HTTP: {(pcapLatest.summary?.http_hosts || []).slice(0, 4).join(", ") || "—"}</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-foreground">Detections</h3>
                  {pcapLatest.detections && pcapLatest.detections.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(() => {
                        const seen = new Set<string>()
                        const unique = (pcapLatest.detections ?? []).filter((d) => {
                          const key = `${d.title ?? ""}|${(d.severity ?? "low")}|${String(d.evidence?.source_ip ?? "")}|${String(d.evidence?.dest_ip ?? "")}`
                          if (seen.has(key)) return false
                          seen.add(key)
                          return true
                        })
                        return unique.map((detection) => {
                        const mlSource = detection.ml_source || "signature"
                        const sourceColors: Record<string, string> = {
                          signature: "bg-blue-500/10 text-blue-500",
                          anomaly: "bg-purple-500/10 text-purple-500",
                          classification: "bg-orange-500/10 text-orange-500",
                        }
                        const sourceLabels: Record<string, string> = {
                          signature: "Heuristic",
                          anomaly: "ML Anomaly",
                          classification: "ML Classification",
                        }
                        const modelType = (detection.evidence?.model_type as string) || "N/A"
                        return (
                          <div key={detection.id} className="p-4 rounded-lg border border-border bg-background">
                            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                              <div className="flex items-center gap-2">
                                <Badge className={getThreatColor(detection.severity || "low")}>
                                  {(detection.severity || "low").toUpperCase()}
                                </Badge>
                                <Badge className={sourceColors[mlSource] || sourceColors.signature} variant="outline">
                                  {sourceLabels[mlSource] || "Heuristic"}
                                </Badge>
                              </div>
                              {detection.confidence !== undefined && (
                                <span className="text-xs text-muted-foreground font-medium">
                                  {(detection.confidence * 100).toFixed(0)}% confidence
                                </span>
                              )}
                            </div>
                            <p className="text-sm font-semibold text-foreground">{detection.title}</p>
                            {detection.description && (
                              <p className="text-xs text-muted-foreground mt-1">{detection.description}</p>
                            )}
                            <div className="text-[11px] text-muted-foreground mt-2 space-y-1">
                              {mlSource !== "signature" && (
                                <div className="flex items-center gap-1">
                                  <span className="font-medium">Model:</span>
                                  <span>{modelType}</span>
                                </div>
                              )}
                              {detection.mitre?.technique && (
                                <div>MITRE: {detection.mitre.technique} ({detection.mitre.tactic})</div>
                              )}
                              {detection.evidence && (
                                <div className="font-mono text-[10px] break-all">
                                  {(detection.evidence as Record<string, unknown>).source_ip != null && (
                                    <div>Source: {String((detection.evidence as Record<string, unknown>).source_ip)}</div>
                                  )}
                                  {(detection.evidence as Record<string, unknown>).dest_ip != null && (
                                    <div>Dest: {String((detection.evidence as Record<string, unknown>).dest_ip)}</div>
                                  )}
                                  {(detection.evidence as Record<string, unknown>).protocol != null && (
                                    <div>Protocol: {String((detection.evidence as Record<string, unknown>).protocol)}</div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        )
                      })})()}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">No detections found in this capture.</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-foreground">Timeline</h3>
                    <div className="space-y-1 text-xs text-muted-foreground max-h-48 overflow-auto pr-1">
                      {(pcapLatest.evidence?.timeline || []).slice(0, 10).map((entry) => (
                        <div key={entry.bucket} className="flex justify-between">
                          <span>{format(new Date(entry.bucket), "HH:mm:ss")}</span>
                          <span className="font-mono">{entry.packets} pkts / {formatBytes(entry.bytes)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-foreground">Top Conversations</h3>
                    <div className="space-y-1 text-xs text-muted-foreground max-h-48 overflow-auto pr-1">
                      {(pcapLatest.evidence?.endpoint_matrix || []).map((edge) => (
                        <div key={`${edge.src}-${edge.dst}`} className="flex justify-between">
                          <span className="font-mono">{edge.src} → {edge.dst}</span>
                          <span className="font-semibold text-foreground">{edge.packets} pkts</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-foreground">Flow Samples</h3>
                    <div className="space-y-1 text-xs text-muted-foreground max-h-48 overflow-auto pr-1">
                      {(pcapLatest.summary?.flow_samples || []).length > 0 ? (
                        (pcapLatest.summary?.flow_samples || []).map((flow) => (
                          <div key={`${flow.src}-${flow.dst}-${flow.dport}`} className="flex justify-between">
                            <span className="font-mono">{flow.src} → {flow.dst} ({flow.proto}/{flow.dport})</span>
                            <span className="font-semibold text-foreground">{flow.packets} pkts</span>
                          </div>
                        ))
                      ) : (
                        <span>—</span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
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
