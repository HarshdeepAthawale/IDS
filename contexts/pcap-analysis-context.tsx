"use client"

import React, { createContext, useContext, useState, useCallback, type ReactNode } from "react"

/** Minimal type for the last PCAP analysis result (persisted across navigation, cleared on refresh). */
export interface LastPcapAnalysisResult {
  metadata?: {
    packets_processed?: number
    bytes_processed?: number
    processing_time_ms?: number
    duration_seconds?: number
    capture_window?: { start?: string | null; end?: string | null }
    cached?: boolean
    filename?: string
    model_info?: {
      ml_enabled?: boolean
      anomaly_detector?: { enabled?: boolean; trained?: boolean }
      classification_detector?: { enabled?: boolean; trained?: boolean }
      detection_counts?: { signature?: number; anomaly?: number; classification?: number }
      average_confidence?: number
      packets_analyzed?: number
      error?: string
      reason?: string
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
  detections?: Array<{
    id: string
    title: string
    severity?: "low" | "medium" | "high" | "critical"
    confidence?: number
    description?: string
    evidence?: Record<string, unknown>
    mitre?: { technique?: string; tactic?: string }
    ml_source?: "signature" | "anomaly" | "classification"
  }>
  risk?: {
    score?: number
    level?: "low" | "medium" | "high" | "critical"
    rationale?: string[]
  }
  evidence?: {
    timeline?: { bucket: string; packets: number; bytes: number }[]
    endpoint_matrix?: { src: string; dst: string; packets: number }[]
  }
}

interface PcapAnalysisContextValue {
  lastPcapResult: LastPcapAnalysisResult | null
  setLastPcapResult: (result: LastPcapAnalysisResult | null) => void
}

const PcapAnalysisContext = createContext<PcapAnalysisContextValue | undefined>(undefined)

export function PcapAnalysisProvider({ children }: { children: ReactNode }) {
  const [lastPcapResult, setLastPcapResultState] = useState<LastPcapAnalysisResult | null>(null)
  const setLastPcapResult = useCallback((result: LastPcapAnalysisResult | null) => {
    setLastPcapResultState(result)
  }, [])
  return (
    <PcapAnalysisContext.Provider value={{ lastPcapResult, setLastPcapResult }}>
      {children}
    </PcapAnalysisContext.Provider>
  )
}

export function usePcapAnalysis() {
  const ctx = useContext(PcapAnalysisContext)
  if (ctx === undefined) {
    throw new Error("usePcapAnalysis must be used within PcapAnalysisProvider")
  }
  return ctx
}
