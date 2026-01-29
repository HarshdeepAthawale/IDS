// API route for alerts - proxy to Flask backend

import { flaskApi, transformers } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Get query parameters
    const { searchParams } = new URL(request.url)
    const params = Object.fromEntries(searchParams.entries())
    
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getAlerts(params)
    
    // Transform Flask response to frontend format
    const alerts = flaskResponse.alerts.map((a) => transformers.alertToFrontend(a as Record<string, unknown>))
    
    return Response.json({
      alerts,
      total: flaskResponse.total,
      summary: flaskResponse.summary
    })
  } catch (error) {
    console.error("Error fetching alerts:", error)
    return Response.json({ error: "Failed to fetch alerts" }, { status: 500 })
  }
}
