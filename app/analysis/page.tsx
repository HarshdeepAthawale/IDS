"use client"

import { useState, useEffect } from "react"
import Layout from "@/components/layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { AlertCircle, Upload, FileText, Network, RefreshCw, Download, CheckCircle } from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { format } from "date-fns"

interface AnalysisResult {
  id: string
  timestamp: string
  source_ip: string
  dest_ip: string
  protocol: string
  packet_size: number
  threat_level: "low" | "medium" | "high" | "critical"
  threat_type: string
  description: string
  confidence: number
  recommendations: string[]
}

interface FlowAnalysisResult {
  flow_id: string
  start_time: string
  end_time: string
  source_ip: string
  dest_ip: string
  protocol: string
  total_packets: number
  total_bytes: number
  duration: number
  threat_score: number
  anomalies: string[]
  patterns: string[]
}

export default function AnalysisPage() {
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([])
  const [flowResults, setFlowResults] = useState<FlowAnalysisResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  
  // Bulk Analysis State
  const [bulkPackets, setBulkPackets] = useState("")
  const [analysisType, setAnalysisType] = useState<"signature" | "anomaly" | "both">("both")
  
  // Flow Analysis State
  const [flowDuration, setFlowDuration] = useState("300") // 5 minutes default
  const [flowThreshold, setFlowThreshold] = useState("0.7")

  const handleBulkAnalysis = async () => {
    if (!bulkPackets.trim()) {
      setError("Please enter packet data to analyze")
      return
    }

    setLoading(true)
    setError(null)
    setProgress(0)

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const packets = bulkPackets.split('\n').filter(line => line.trim())
      const response = await flaskApi.analyzeBulkPackets({
        packets: packets.map(packet => ({
          data: packet.trim(),
          timestamp: new Date().toISOString()
        })),
        analysis_type: analysisType
      })

      clearInterval(progressInterval)
      setProgress(100)

      // Transform results
      const transformedResults = response.results.map((result: any, index: number) => ({
        id: `bulk_${index}`,
        timestamp: new Date().toISOString(),
        source_ip: result.source_ip || "Unknown",
        dest_ip: result.dest_ip || "Unknown",
        protocol: result.protocol || "Unknown",
        packet_size: result.packet_size || 0,
        threat_level: result.threat_level || "low",
        threat_type: result.threat_type || "Unknown",
        description: result.description || "No threat detected",
        confidence: result.confidence || 0,
        recommendations: result.recommendations || []
      }))

      setAnalysisResults(transformedResults)
    } catch (err) {
      console.error('Error analyzing bulk packets:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze packets'
      setError(`Failed to analyze packets. Backend service is required. ${errorMessage}`)
      setAnalysisResults([]) // Empty, no mock data
    } finally {
      setLoading(false)
      setTimeout(() => setProgress(0), 1000)
    }
  }

  const handleFlowAnalysis = async () => {
    setLoading(true)
    setError(null)
    setProgress(0)

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 15, 90))
      }, 300)

      const response = await flaskApi.analyzeFlow({
        duration_seconds: parseInt(flowDuration),
        threat_threshold: parseFloat(flowThreshold),
        analysis_type: "network_flow"
      })

      clearInterval(progressInterval)
      setProgress(100)

      // Transform results
      const transformedResults = response.flows.map((flow: any) => ({
        flow_id: flow.flow_id,
        start_time: flow.start_time,
        end_time: flow.end_time,
        source_ip: flow.source_ip,
        dest_ip: flow.dest_ip,
        protocol: flow.protocol,
        total_packets: flow.total_packets,
        total_bytes: flow.total_bytes,
        duration: flow.duration,
        threat_score: flow.threat_score,
        anomalies: flow.anomalies || [],
        patterns: flow.patterns || []
      }))

      setFlowResults(transformedResults)
    } catch (err) {
      console.error('Error analyzing flows:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze network flows'
      setError(`Failed to analyze network flows. Backend service is required. ${errorMessage}`)
      setFlowResults([]) // Empty, no mock data
    } finally {
      setLoading(false)
      setTimeout(() => setProgress(0), 1000)
    }
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

  const exportResults = (type: "packets" | "flows") => {
    const data = type === "packets" ? analysisResults : flowResults
    const csvContent = [
      Object.keys(data[0] || {}),
      ...data.map(item => Object.values(item))
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${type}-analysis-${format(new Date(), 'yyyy-MM-dd')}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Packet Analysis</h1>
            <p className="text-muted-foreground mt-2">Advanced packet analysis and network flow investigation</p>
          </div>
          <div className="flex items-center gap-2">
            {analysisResults.length > 0 && (
              <Button onClick={() => exportResults("packets")} variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export Packets
              </Button>
            )}
            {flowResults.length > 0 && (
              <Button onClick={() => exportResults("flows")} variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export Flows
              </Button>
            )}
          </div>
        </div>


        {/* Analysis Tabs */}
        <Tabs defaultValue="bulk" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="bulk" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Bulk Packet Analysis
            </TabsTrigger>
            <TabsTrigger value="flow" className="flex items-center gap-2">
              <Network className="h-4 w-4" />
              Flow Analysis
            </TabsTrigger>
          </TabsList>

          {/* Bulk Packet Analysis */}
          <TabsContent value="bulk" className="space-y-4">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Bulk Packet Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Analysis Type</label>
                    <Select value={analysisType} onValueChange={(value: any) => setAnalysisType(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="signature">Signature Detection</SelectItem>
                        <SelectItem value="anomaly">Anomaly Detection</SelectItem>
                        <SelectItem value="both">Both (Signature + Anomaly)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Packet Data</label>
                    <Textarea
                      placeholder="Enter packet data (one per line)..."
                      value={bulkPackets}
                      onChange={(e) => setBulkPackets(e.target.value)}
                      rows={6}
                      className="font-mono text-xs"
                    />
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <Button 
                    onClick={handleBulkAnalysis} 
                    disabled={loading || !bulkPackets.trim()}
                    className="flex items-center gap-2"
                  >
                    {loading ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <AlertCircle className="h-4 w-4" />
                    )}
                    Analyze Packets
                  </Button>
                  {loading && (
                    <div className="flex-1">
                      <Progress value={progress} className="h-2" />
                    </div>
                  )}
                </div>

                {error && (
                  <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                    {error}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Bulk Analysis Results */}
            {analysisResults.length > 0 && (
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    Analysis Results ({analysisResults.length} packets)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {analysisResults.map((result) => (
                      <div key={result.id} className="p-4 rounded-lg bg-background border border-border">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-semibold px-2 py-1 rounded ${getThreatColor(result.threat_level)}`}>
                              {result.threat_level.toUpperCase()}
                            </span>
                            <span className="text-xs text-muted-foreground">{result.threat_type}</span>
                            <span className="text-xs text-muted-foreground">
                              Confidence: {(result.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(result.timestamp), 'HH:mm:ss')}
                          </span>
                        </div>
                        
                        <p className="text-sm font-medium text-foreground mb-2">{result.description}</p>
                        
                        <div className="flex gap-4 text-xs text-muted-foreground mb-3">
                          <span>From: {result.source_ip}</span>
                          <span>To: {result.dest_ip}</span>
                          <span>{result.protocol}</span>
                          <span>Size: {result.packet_size} bytes</span>
                        </div>

                        {result.recommendations.length > 0 && (
                          <div>
                            <span className="text-xs text-muted-foreground mb-1 block">Recommendations:</span>
                            <ul className="text-xs text-muted-foreground space-y-1">
                              {result.recommendations.map((rec, index) => (
                                <li key={index} className="flex items-center gap-1">
                                  <span className="text-green-500">•</span>
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Flow Analysis */}
          <TabsContent value="flow" className="space-y-4">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Network className="h-5 w-5" />
                  Network Flow Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Analysis Duration (seconds)</label>
                    <Select value={flowDuration} onValueChange={setFlowDuration}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="60">1 minute</SelectItem>
                        <SelectItem value="300">5 minutes</SelectItem>
                        <SelectItem value="600">10 minutes</SelectItem>
                        <SelectItem value="1800">30 minutes</SelectItem>
                        <SelectItem value="3600">1 hour</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Threat Threshold</label>
                    <Select value={flowThreshold} onValueChange={setFlowThreshold}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0.5">Low (0.5)</SelectItem>
                        <SelectItem value="0.7">Medium (0.7)</SelectItem>
                        <SelectItem value="0.8">High (0.8)</SelectItem>
                        <SelectItem value="0.9">Critical (0.9)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <Button 
                    onClick={handleFlowAnalysis} 
                    disabled={loading}
                    className="flex items-center gap-2"
                  >
                    {loading ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Network className="h-4 w-4" />
                    )}
                    Analyze Flows
                  </Button>
                  {loading && (
                    <div className="flex-1">
                      <Progress value={progress} className="h-2" />
                    </div>
                  )}
                </div>

                {error && (
                  <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                    {error}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Flow Analysis Results */}
            {flowResults.length > 0 && (
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    Flow Analysis Results ({flowResults.length} flows)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {flowResults.map((flow) => (
                      <div key={flow.flow_id} className="p-4 rounded-lg bg-background border border-border">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-semibold px-2 py-1 rounded ${
                              flow.threat_score > 0.8 ? 'bg-destructive/10 text-destructive' :
                              flow.threat_score > 0.6 ? 'bg-orange-500/10 text-orange-500' :
                              'bg-green-500/10 text-green-500'
                            }`}>
                              Threat Score: {(flow.threat_score * 100).toFixed(1)}%
                            </span>
                            <span className="text-xs text-muted-foreground">{flow.protocol}</span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(flow.start_time), 'HH:mm:ss')} - {format(new Date(flow.end_time), 'HH:mm:ss')}
                          </span>
                        </div>
                        
                        <div className="flex gap-4 text-xs text-muted-foreground mb-3">
                          <span>From: {flow.source_ip}</span>
                          <span>To: {flow.dest_ip}</span>
                          <span>Packets: {flow.total_packets}</span>
                          <span>Bytes: {(flow.total_bytes / 1024 / 1024).toFixed(2)} MB</span>
                          <span>Duration: {flow.duration}s</span>
                        </div>

                        {flow.anomalies.length > 0 && (
                          <div className="mb-3">
                            <span className="text-xs text-muted-foreground mb-1 block">Anomalies Detected:</span>
                            <div className="flex flex-wrap gap-1">
                              {flow.anomalies.map((anomaly, index) => (
                                <Badge key={index} variant="destructive" className="text-xs">
                                  {anomaly}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {flow.patterns.length > 0 && (
                          <div>
                            <span className="text-xs text-muted-foreground mb-1 block">Patterns Identified:</span>
                            <div className="flex flex-wrap gap-1">
                              {flow.patterns.map((pattern, index) => (
                                <Badge key={index} variant="secondary" className="text-xs">
                                  {pattern}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  )
}
