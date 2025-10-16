// API utility functions for fetching security monitoring data

export interface Alert {
  id: string
  timestamp: string
  sourceIp: string
  destIp: string
  protocol: string
  type: "signature" | "anomaly"
  severity: "critical" | "high" | "medium" | "low"
  description: string
}

export interface InsiderThreat {
  id: string
  timestamp: string
  user: string
  activity: string
  riskLevel: "critical" | "high" | "medium" | "low"
}

export interface TrafficData {
  time: string
  packets: number
  bytes: number
}

export interface ProtocolData {
  name: string
  value: number
}

export interface DashboardStats {
  totalAlerts: number
  criticalAlerts: number
  activeConnections: number
  totalPackets: number
}

// Fetch dashboard statistics
export async function fetchDashboardStats(): Promise<DashboardStats> {
  try {
    const response = await fetch("/api/stats")
    if (!response.ok) throw new Error("Failed to fetch stats")
    return response.json()
  } catch (error) {
    console.error("Error fetching dashboard stats:", error)
    // Return mock data as fallback
    return {
      totalAlerts: 1247,
      criticalAlerts: 23,
      activeConnections: 156,
      totalPackets: 2847392,
    }
  }
}

// Fetch recent alerts
export async function fetchAlerts(): Promise<Alert[]> {
  try {
    const response = await fetch("/api/alerts")
    if (!response.ok) throw new Error("Failed to fetch alerts")
    return response.json()
  } catch (error) {
    console.error("Error fetching alerts:", error)
    return []
  }
}

// Fetch traffic statistics
export async function fetchTrafficStats(): Promise<{
  trafficData: TrafficData[]
  protocolData: ProtocolData[]
}> {
  try {
    const response = await fetch("/api/traffic")
    if (!response.ok) throw new Error("Failed to fetch traffic stats")
    return response.json()
  } catch (error) {
    console.error("Error fetching traffic stats:", error)
    return { trafficData: [], protocolData: [] }
  }
}

// Fetch insider threats
export async function fetchInsiderThreats(): Promise<InsiderThreat[]> {
  try {
    const response = await fetch("/api/threats")
    if (!response.ok) throw new Error("Failed to fetch insider threats")
    return response.json()
  } catch (error) {
    console.error("Error fetching insider threats:", error)
    return []
  }
}

// Subscribe to real-time updates via WebSocket
export function subscribeToUpdates(callback: (data: { type: string; payload: unknown }) => void): () => void {
  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  const connect = () => {
    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      ws = new WebSocket(`${protocol}//${window.location.host}/api/ws`)

      ws.onopen = () => {
        console.log("WebSocket connected")
        reconnectAttempts = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          callback(data)
        } catch (error) {
          console.error("Error parsing WebSocket message:", error)
        }
      }

      ws.onerror = (error) => {
        console.error("WebSocket error:", error)
      }

      ws.onclose = () => {
        console.log("WebSocket disconnected")
        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          setTimeout(connect, reconnectDelay)
        }
      }
    } catch (error) {
      console.error("Error connecting to WebSocket:", error)
    }
  }

  connect()

  // Return cleanup function
  return () => {
    if (ws) {
      ws.close()
    }
  }
}
