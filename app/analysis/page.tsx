"use client"

import { useState, Suspense } from "react"
import { useRouter } from "next/navigation"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Upload, RefreshCw, CheckCircle, ShieldCheck, Activity, Copy, FileJson } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { format } from "date-fns"
import { usePcapAnalysis } from "@/contexts/pcap-analysis-context"

interface PcapDetection {
  id: string
  title: string
  severity: "low" | "medium" | "high" | "critical"
  confidence?: number
  description?: string
  evidence?: Record<string, any>
  mitre?: { technique?: string; tactic?: string }
  ml_source?: "signature" | "anomaly" | "classification"
}

interface PcapSummary {
  top_protocols?: { name: string; count: number; percentage?: number }[]
  top_talkers?: { ip: string; packets: number }[]
  top_ports?: { port: number; packets: number }[]
  dns_queries?: string[]
  tls_handshakes?: { server: string; port: number }[]
  http_hosts?: string[]
  flow_samples?: { src: string; dst: string; proto: string; dport: number; packets: number }[]
}

interface PcapRisk {
  score?: number
  level?: "low" | "medium" | "high" | "critical"
  rationale?: string[]
  risk_source?: "classification" | "severity" | "unavailable"
  classification_model_type?: string
}

interface PcapModelInfo {
  ml_enabled?: boolean
  anomaly_detector?: {
    enabled?: boolean
    trained?: boolean
  }
  classification_detector?: {
    enabled?: boolean
    trained?: boolean
  }
  classification_model_type?: string | null
  detection_counts?: {
    signature?: number
    anomaly?: number
    classification?: number
  }
  average_confidence?: number
  packets_analyzed?: number
  error?: string
  reason?: string
}

interface PcapAnalysisResponse {
  id?: string
  metadata?: {
    packets_processed?: number
    bytes_processed?: number
    processing_time_ms?: number
    duration_seconds?: number
    capture_window?: { start?: string | null; end?: string | null }
    cached?: boolean
    filename?: string
    model_info?: PcapModelInfo
  }
  summary?: PcapSummary
  detections?: PcapDetection[]
  risk?: PcapRisk
  evidence?: {
    timeline?: { bucket: string; packets: number; bytes: number }[]
    endpoint_matrix?: { src: string; dst: string; packets: number }[]
  }
}

function AnalysisPageContent() {
  const router = useRouter()
  const { lastPcapResult, setLastPcapResult } = usePcapAnalysis()
  const pcapResult = lastPcapResult as PcapAnalysisResponse | null
  const [pcapFile, setPcapFile] = useState<File | null>(null)
  const [pcapLoading, setPcapLoading] = useState(false)
  const [pcapError, setPcapError] = useState<string | null>(null)
  const [pcapProgress, setPcapProgress] = useState(0)

  const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB
  const validatePcapFile = (file: File): string | null => {
    const validExtensions = ['.pcap', '.pcapng', '.csv']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))

    if (!validExtensions.includes(fileExtension)) {
      return `Invalid file type. Please upload a .pcap, .pcapng, or .csv file.`
    }

    if (file.size > MAX_FILE_SIZE) {
      return `File size exceeds 100MB limit. Please upload a smaller file.`
    }

    if (file.size === 0) {
      return `File is empty. Please upload a valid file.`
    }

    return null
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getThreatColor = (level: string) => {
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

  const formatBytes = (bytes?: number) => {
    if (!bytes && bytes !== 0) return "N/A"
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds && seconds !== 0) return "N/A"
    if (seconds < 60) return `${Math.round(seconds)}s`
    const minutes = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${minutes}m ${secs}s`
  }

  const handlePcapAnalyze = async () => {
    if (!pcapFile) {
      setPcapError("Please choose a PCAP file to analyze")
      return
    }

    const validationError = validatePcapFile(pcapFile)
    if (validationError) {
      setPcapError(validationError)
      return
    }

    setPcapLoading(true)
    setPcapError(null)
    setPcapProgress(0)

    const progressInterval = setInterval(() => {
      setPcapProgress((prev) => Math.min(prev + 8, 92))
    }, 180)

    try {
      const response = await flaskApi.analyzePcap({
        file: pcapFile,
        maxPackets: 100000,
      })
      setLastPcapResult(response)
      setPcapProgress(100)
      // Redirect to stored summary so user can revisit anytime via /analysis/[id]
      if (response?.id) {
        router.push(`/analysis/${response.id}`)
      }
    } catch (err) {
      console.error("Error analyzing PCAP:", err)
      let message = "Failed to analyze PCAP"
      if (err instanceof Error) {
        message = err.message
        if (message.includes("fetch") || message.includes("Network") || message.includes("Failed to fetch")) {
          message = "Cannot reach the backend. Ensure the Flask backend is running (e.g. port 3002), or run with Docker: docker compose up -d"
        }
      }
      setPcapError(message)
      setLastPcapResult(null)
    } finally {
      clearInterval(progressInterval)
      setPcapLoading(false)
      setTimeout(() => setPcapProgress(0), 800)
    }
  }

  const exportPcapResults = () => {
    if (!pcapResult) return

    const jsonContent = JSON.stringify(pcapResult, null, 2)
    const blob = new Blob([jsonContent], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pcap-analysis-${pcapResult.metadata?.filename || 'results'}-${format(new Date(), 'yyyy-MM-dd')}.json`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const copyPcapSummary = async () => {
    if (!pcapResult) return

    const summary = `PCAP Analysis Summary
Risk Score: ${pcapResult.risk?.score ?? 'N/A'} (${pcapResult.risk?.level?.toUpperCase() ?? 'N/A'})
Total Packets: ${pcapResult.metadata?.packets_processed ?? 'N/A'}
Bytes: ${formatBytes(pcapResult.metadata?.bytes_processed)}
Duration: ${formatDuration(pcapResult.metadata?.duration_seconds)}
Processing Time: ${pcapResult.metadata?.processing_time_ms}ms
Detections: ${pcapResult.detections?.length ?? 0}
${pcapResult.metadata?.model_info?.ml_enabled ? `
ML Models:
- Anomaly Detector: ${pcapResult.metadata.model_info.anomaly_detector?.trained ? 'Trained ✓' : 'Not Trained ✗'}
- Classification: ${pcapResult.metadata.model_info.classification_model_type === 'secids_cnn' ? 'SecIDS-CNN' : 'Classifier'} ${pcapResult.metadata.model_info.classification_detector?.enabled ? (pcapResult.metadata.model_info.classification_detector?.trained ? '✓' : '✗') : 'Not Enabled'}
- Average Confidence: ${pcapResult.metadata.model_info.average_confidence ? (pcapResult.metadata.model_info.average_confidence * 100).toFixed(1) + '%' : 'N/A'}
` : ''}
`

    try {
      await navigator.clipboard.writeText(summary)
      alert('Summary copied to clipboard!')
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Packet Analysis</h1>
          <p className="text-muted-foreground mt-2">Upload a PCAP file for analysis. Results appear here and on Dashboard, Summary, and Alerts.</p>
        </div>

        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              PCAP Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Upload PCAP/CSV</label>
                <Input
                  type="file"
                  accept=".pcap,.pcapng,.csv"
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    if (file) {
                      const validationError = validatePcapFile(file)
                      if (validationError) {
                        setPcapError(validationError)
                        setPcapFile(null)
                        event.target.value = ''
                      } else {
                        setPcapError(null)
                        setPcapFile(file)
                      }
                    } else {
                      setPcapFile(null)
                      setPcapError(null)
                    }
                  }}
                  className="cursor-pointer"
                />
                <p className="text-xs text-muted-foreground">
                  {pcapFile ? (
                    <span>
                      Selected: <span className="font-medium">{pcapFile.name}</span> ({formatFileSize(pcapFile.size)})
                    </span>
                  ) : (
                    "Up to 100,000 packets analyzed per request. Supports .pcap and .pcapng (max 100MB)."
                  )}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <Button
                  onClick={handlePcapAnalyze}
                  disabled={pcapLoading || !pcapFile}
                  className="flex items-center gap-2"
                >
                  {pcapLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  Analyze PCAP
                </Button>
                {pcapLoading && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{pcapFile ? `Processing ${pcapFile.name}...` : "Processing..."}</span>
                      <span>{pcapProgress}%</span>
                    </div>
                    <Progress value={pcapProgress} className="h-2" />
                  </div>
                )}
                {pcapError && (
                  <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm space-y-1">
                    <div className="font-medium">Error</div>
                    <div>{pcapError}</div>
                    {(pcapError.includes("backend") || pcapError.includes("Cannot reach")) && (
                      <div className="text-xs mt-2 pt-2 border-t border-destructive/20">
                        <strong>Troubleshooting:</strong>
                        <ul className="list-disc list-inside mt-1 space-y-0.5">
                          <li>Run with Docker: <code className="bg-destructive/20 px-1 rounded">docker compose up -d</code> (starts backend, frontend, MongoDB)</li>
                          <li>Or run backend locally: <code className="bg-destructive/20 px-1 rounded">cd backend && ./venv/bin/python app.py</code> (use venv; install deps first: <code className="bg-destructive/20 px-1 rounded">pip install -r requirements.txt</code> inside venv)</li>
                          <li>Verify backend URL: <code className="bg-destructive/20 px-1 rounded">http://localhost:3002</code></li>
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {pcapResult && (
          <>
            <Card className="bg-card border-border border-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    Analysis Summary
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button
                      onClick={copyPcapSummary}
                      variant="outline"
                      size="sm"
                      className="gap-2"
                    >
                      <Copy className="h-4 w-4" />
                      Copy Summary
                    </Button>
                    <Button
                      onClick={exportPcapResults}
                      variant="outline"
                      size="sm"
                      className="gap-2"
                    >
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
                          {!pcapResult.metadata?.model_info?.ml_enabled && (
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
                      {pcapResult.metadata?.model_info?.ml_enabled ? (
                        <>
                          <div className="flex items-center gap-1 text-xs">
                            <Badge variant={pcapResult.metadata.model_info.anomaly_detector?.trained ? "default" : "secondary"} className="text-[10px]">
                              Anomaly {pcapResult.metadata.model_info.anomaly_detector?.trained ? "✓" : "✗"}
                            </Badge>
                          </div>
                          {pcapResult.metadata.model_info.classification_detector?.enabled && (
                            <div className="flex items-center gap-1 text-xs">
                              <Badge variant={pcapResult.metadata.model_info.classification_detector?.trained ? "default" : "secondary"} className="text-[10px]">
                                {pcapResult.metadata.model_info.classification_model_type === "secids_cnn"
                                  ? "SecIDS-CNN"
                                  : "Classify"}{" "}
                                {pcapResult.metadata.model_info.classification_detector?.trained ? "✓" : "✗"}
                              </Badge>
                            </div>
                          )}
                          {pcapResult.metadata.model_info.average_confidence && (
                            <div className="text-xs text-muted-foreground">
                              Avg Confidence: {(pcapResult.metadata.model_info.average_confidence * 100).toFixed(1)}%
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-xs text-muted-foreground">Traditional only · ML integration planned</div>
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
                      <div>DNS queries: {(pcapResult.summary?.dns_queries || []).slice(0, 5).join(", ") || "—"}</div>
                      <div>TLS servers: {(pcapResult.summary?.tls_handshakes || []).slice(0, 3).map((tls) => tls.server).join(", ") || "—"}</div>
                      <div>HTTP hosts: {(pcapResult.summary?.http_hosts || []).slice(0, 4).join(", ") || "—"}</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-foreground">Detections</h3>
                  {(pcapResult.detections && pcapResult.detections.length > 0) ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(() => {
                        const seen = new Set<string>()
                        const unique = (pcapResult.detections ?? []).filter((d) => {
                          const key = `${d.title ?? ""}|${(d.severity ?? "low")}|${(d.evidence as Record<string, unknown>)?.source_ip ?? ""}|${(d.evidence as Record<string, unknown>)?.dest_ip ?? ""}`
                          if (seen.has(key)) return false
                          seen.add(key)
                          return true
                        })
                        return unique.map((detection) => {
                        const mlSource = detection.ml_source || "signature"
                        const sourceColors = {
                          signature: "bg-blue-500/10 text-blue-500",
                          anomaly: "bg-purple-500/10 text-purple-500",
                          classification: "bg-orange-500/10 text-orange-500"
                        }
                        const sourceLabels = {
                          signature: "Heuristic",
                          anomaly: "ML Anomaly",
                          classification: "ML Classification"
                        }
                        const modelType = detection.evidence?.model_type || "N/A"

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
                                  {detection.evidence.source_ip && (
                                    <div>Source: {detection.evidence.source_ip}</div>
                                  )}
                                  {detection.evidence.dest_ip && (
                                    <div>Dest: {detection.evidence.dest_ip}</div>
                                  )}
                                  {detection.evidence.protocol && (
                                    <div>Protocol: {detection.evidence.protocol}</div>
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
                        <span>Flows will appear after analysis.</span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </Layout>
  )
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={
      <Layout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-muted-foreground">Loading analysis...</div>
        </div>
      </Layout>
    }>
      <AnalysisPageContent />
    </Suspense>
  )
}
