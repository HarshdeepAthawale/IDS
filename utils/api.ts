// API utility functions for Flask backend integration
// Replace BASE_URL with your Flask backend URL

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE"
  headers?: Record<string, string>
  body?: any
}

async function apiCall(endpoint: string, options: FetchOptions = {}) {
  const url = `${BASE_URL}${endpoint}`
  const defaultHeaders = {
    "Content-Type": "application/json",
  }

  try {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: { ...defaultHeaders, ...options.headers },
      body: options.body ? JSON.stringify(options.body) : undefined,
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    console.error("API call failed:", error)
    throw error
  }
}

// Alert endpoints
export const alertsAPI = {
  getAlerts: () => apiCall("/alerts"),
  getAlertById: (id: string) => apiCall(`/alerts/${id}`),
  createAlert: (data: any) => apiCall("/alerts", { method: "POST", body: data }),
}

// Traffic stats endpoints
export const statsAPI = {
  getTrafficStats: () => apiCall("/stats/traffic"),
  getProtocolDistribution: () => apiCall("/stats/protocols"),
  getConnectionStats: () => apiCall("/stats/connections"),
}

// Insider threats endpoints
export const insiderAPI = {
  getThreats: () => apiCall("/insider-threats"),
  getThreatById: (id: string) => apiCall(`/insider-threats/${id}`),
  updateThreatStatus: (id: string, status: string) =>
    apiCall(`/insider-threats/${id}`, { method: "PUT", body: { status } }),
}

// WebSocket setup for real-time updates (optional)
export function setupWebSocket(url: string, onMessage: (data: any) => void) {
  const ws = new WebSocket(url)

  ws.onopen = () => {
    console.log("WebSocket connected")
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error)
    }
  }

  ws.onerror = (error) => {
    console.error("WebSocket error:", error)
  }

  ws.onclose = () => {
    console.log("WebSocket disconnected")
  }

  return ws
}
