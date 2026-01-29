"use client"

import { useState, useEffect, use } from "react"
import Link from "next/link"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, CheckCircle, Activity, Copy, FileJson } from "lucide-react"
import { format } from "date-fns"

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

interface PcapAnalysisResponse {
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
      classification_model_type?: string | null
      detection_counts?: { signature?: number; anomaly?: number; classification?: number }
      average_confidence?: number
    }
  }
  summary?: {
    top_protocols?: { name: string; count: number; percentage?: number }[]
    top_talkers?: { ip: string; packets: number }[]
    top_ports?: { port: number; packets: number }[]
    dns_queries?: string[]
    tls_handshakes?: { server: string; port: number }[]
    http_hosts?: string[]
    flow_samples?: { src: string; dst: string; proto: string; dport: number; packets: number }[]
  }
  detections?: PcapDetection[]
  risk?: {
    score?: number
    level?: string
    rationale?: string[]
    risk_source?: string
    classification_model_type?: string
  }
  evidence?: {
    timeline?: { bucket: string; packets: number; bytes: number }[]
    endpoint_matrix?: { src: string; dst: string; packets: number }[]
  }
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

export default function AnalysisDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [result, setResult] = useState<PcapAnalysisResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchAnalysis() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`/api/pcap/analyses/${encodeURIComponent(id)}`)
        const data = await res.json().catch(() => ({}))
        if (cancelled) return
        if (!res.ok) {
          setError(data.error || "Failed to load analysis")
          setResult(null)
          return
        }
        setResult(data)
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load analysis")
          setResult(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchAnalysis()
    return () => { cancelled = true }
  }, [id])

  const exportJson = () => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `pcap-analysis-${result.metadata?.filename || id}-${format(new Date(), "yyyy-MM-dd")}.json`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const copySummary = async () => {
    if (!result) return
    const summary = `PCAP Analysis Summary
Risk Score: ${result.risk?.score ?? "N/A"} (${(result.risk?.level ?? "low").toUpperCase()})
Total Packets: ${result.metadata?.packets_processed ?? "N/A"}
Bytes: ${formatBytes(result.metadata?.bytes_processed)}
Duration: ${formatDuration(result.metadata?.duration_seconds)}
Processing Time: ${result.metadata?.processing_time_ms}ms
Detections: ${result.detections?.length ?? 0}
`
    try {
      await navigator.clipboard.writeText(summary)
      alert("Summary copied to clipboard!")
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="space-y-6">
          <Button asChild variant="ghost" size="sm" className="gap-2">
            <Link href="/analysis">
              <ArrowLeft className="h-4 w-4" />
              Back to analysis
            </Link>
          </Button>
          <div className="flex items-center justify-center min-h-[300px] text-muted-foreground">
            Loading analysis...
          </div>
        </div>
      </Layout>
    )
  }

  if (error || !result) {
    return (
      <Layout>
        <div className="space-y-6">
          <Button asChild variant="ghost" size="sm" className="gap-2">
            <Link href="/analysis">
              <ArrowLeft className="h-4 w-4" />
              Back to analysis
            </Link>
          </Button>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <p className="text-destructive">{error || "Analysis not found."}</p>
              <Button asChild variant="outline" size="sm" className="mt-4">
                <Link href="/analysis">View all analyses</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </Layout>
    )
  }

  const pcapResult = result

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <Button asChild variant="ghost" size="sm" className="gap-2">
            <Link href="/analysis">
              <ArrowLeft className="h-4 w-4" />
              Back to analysis
            </Link>
          </Button>
          {pcapResult.metadata?.filename && (
            <p className="text-sm text-muted-foreground truncate max-w-[280px]" title={pcapResult.metadata.filename}>
              {pcapResult.metadata.filename}
            </p>
          )}
        </div>

        <Card className="bg-card border-border border-2">
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                Full PCAP Analysis
                {pcapResult.metadata?.filename && (
                  <span className="text-xs font-normal text-muted-foreground">({pcapResult.metadata.filename})</span>
                )}
              </CardTitle>
              <div className="flex gap-2">
                <Button onClick={copySummary} variant="outline" size="sm" className="gap-2">
                  <Copy className="h-4 w-4" />
                  Copy Summary
                </Button>
                <Button onClick={exportJson} variant="outline" size="sm" className="gap-2">
                  <FileJson className="h-4 w-4" />
                  Export JSON
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-xs text-muted-foreground mb-1">Risk Score</div>
                <div className="flex items-center gap-2">
                  <div className="text-2xl font-bold">{pcapResult.risk?.score ?? "--"}</div>
                  <Badge className={getThreatColor(pcapResult.risk?.level || "low")}>
                    {(pcapResult.risk?.level || "low").toUpperCase()}
                  </Badge>
                </div>
                <div className="text-[10px] text-muted-foreground mt-1">
                  {pcapResult.risk?.risk_source === "classification"
                    ? (pcapResult.risk?.classification_model_type === "secids_cnn"
                      ? "SecIDS-CNN classification risk (0–100)."
                      : "Classification model risk (0–100).")
                    : pcapResult.risk?.risk_source === "unavailable"
                      ? "Enable SecIDS-CNN for ML risk score."
                      : "Baseline + severity per detection (0–100)."}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-xs text-muted-foreground mb-1">Total Packets</div>
                <div className="text-2xl font-bold">{pcapResult.metadata?.packets_processed ?? "--"}</div>
                <div className="text-xs text-muted-foreground">{formatBytes(pcapResult.metadata?.bytes_processed)}</div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-xs text-muted-foreground mb-1">Duration</div>
                <div className="text-2xl font-bold">{formatDuration(pcapResult.metadata?.duration_seconds)}</div>
                <div className="text-xs text-muted-foreground">{pcapResult.metadata?.processing_time_ms}ms</div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-xs text-muted-foreground mb-1">Detections</div>
                <div className="text-2xl font-bold">{pcapResult.detections?.length ?? 0}</div>
                <div className="text-xs text-muted-foreground">
                  {pcapResult.metadata?.model_info?.detection_counts ? (
                    <>
                      ML: {(pcapResult.metadata.model_info.detection_counts.anomaly ?? 0) + (pcapResult.metadata.model_info.detection_counts.classification ?? 0)} |
                      Heuristic: {pcapResult.metadata.model_info.detection_counts.signature ?? 0}
                    </>
                  ) : (
                    "Traditional heuristics"
                  )}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-xs text-muted-foreground mb-1">ML Models</div>
                <div className="space-y-1">
                  {pcapResult.metadata?.model_info?.ml_enabled ? (
                    <>
                      <Badge variant={pcapResult.metadata.model_info.anomaly_detector?.trained ? "default" : "secondary"} className="text-[10px]">
                        Anomaly {pcapResult.metadata.model_info.anomaly_detector?.trained ? "✓" : "✗"}
                      </Badge>
                      {pcapResult.metadata.model_info.classification_detector?.enabled && (
                        <Badge variant={pcapResult.metadata.model_info.classification_detector?.trained ? "default" : "secondary"} className="text-[10px] ml-1">
                          {pcapResult.metadata.model_info.classification_model_type === "secids_cnn" ? "SecIDS-CNN" : "Classify"}{" "}
                          {pcapResult.metadata.model_info.classification_detector?.trained ? "✓" : "✗"}
                        </Badge>
                      )}
                      {pcapResult.metadata.model_info.average_confidence != null && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Avg Confidence: {(pcapResult.metadata.model_info.average_confidence * 100).toFixed(1)}%
                        </div>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-muted-foreground">Traditional only</span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              PCAP Findings
              {pcapResult.metadata?.filename && (
                <span className="text-xs text-muted-foreground">({pcapResult.metadata.filename})</span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground">Top Protocols</h3>
                <div className="flex flex-wrap gap-2">
                  {(pcapResult.summary?.top_protocols || []).map((proto) => (
                    <Badge key={proto.name} variant="secondary" className="text-xs">
                      {proto.name}: {proto.percentage ? `${proto.percentage}%` : proto.count}
                    </Badge>
                  ))}
                </div>
                <h3 className="text-sm font-semibold text-foreground">Top Talkers</h3>
                <div className="space-y-1 text-xs text-muted-foreground">
                  {(pcapResult.summary?.top_talkers || []).map((talker) => (
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
                  {(pcapResult.summary?.top_ports || []).map((port) => (
                    <Badge key={port.port} variant="outline" className="text-xs">
                      {port.port} ({port.packets} pkts)
                    </Badge>
                  ))}
                </div>
                <h3 className="text-sm font-semibold text-foreground">DNS / TLS / HTTP</h3>
                <div className="text-xs text-muted-foreground space-y-1">
                  <div>DNS: {(pcapResult.summary?.dns_queries || []).slice(0, 5).join(", ") || "—"}</div>
                  <div>TLS: {(pcapResult.summary?.tls_handshakes || []).slice(0, 3).map((t) => t.server).join(", ") || "—"}</div>
                  <div>HTTP: {(pcapResult.summary?.http_hosts || []).slice(0, 4).join(", ") || "—"}</div>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Detections from PCAP</h3>
              {pcapResult.detections && pcapResult.detections.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(() => {
                    const seen = new Set<string>()
                    const unique = (pcapResult.detections ?? []).filter((d) => {
                      const key = `${d.title ?? ""}|${d.severity ?? "low"}|${d.evidence?.source_ip ?? ""}|${d.evidence?.dest_ip ?? ""}`
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
                          <p className="text-xs text-muted-foreground mt-1">{detection.description}</p>
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
                                {(detection.evidence as Record<string, unknown>).source_ip != null && <div>Source: {String((detection.evidence as Record<string, unknown>).source_ip)}</div>}
                                {(detection.evidence as Record<string, unknown>).dest_ip != null && <div>Dest: {String((detection.evidence as Record<string, unknown>).dest_ip)}</div>}
                                {(detection.evidence as Record<string, unknown>).protocol != null && <div>Protocol: {String((detection.evidence as Record<string, unknown>).protocol)}</div>}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })
                  })()}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No detections found in this capture.</p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-foreground">Timeline</h3>
                <div className="space-y-1 text-xs text-muted-foreground max-h-48 overflow-auto pr-1">
                  {(pcapResult.evidence?.timeline || []).slice(0, 10).map((entry) => (
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
                  {(pcapResult.evidence?.endpoint_matrix || []).map((edge) => (
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
                  {(pcapResult.summary?.flow_samples || []).length > 0 ? (
                    (pcapResult.summary?.flow_samples || []).map((flow) => (
                      <div key={`${flow.src}-${flow.dst}-${flow.dport}`} className="flex justify-between">
                        <span className="font-mono">{flow.src} → {flow.dst} ({flow.proto}/{flow.dport})</span>
                        <span className="font-semibold text-foreground">{flow.packets} pkts</span>
                      </div>
                    ))
                  ) : (
                    <span>No flow samples.</span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}
