// API route for alert history - proxy to Flask backend

import { flaskApi, transformers } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Get query parameters
    const { searchParams } = new URL(request.url)
    const params = Object.fromEntries(searchParams.entries())
    
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getAlertHistory(params)
    
    // Transform Flask response to frontend format
    const alerts = flaskResponse.alerts.map(transformers.alertToFrontend)
    
    return Response.json({
      alerts,
      total: flaskResponse.total,
      summary: flaskResponse.summary
    })
  } catch (error) {
    console.error("Error fetching alert history:", error)
    return Response.json({ error: "Failed to fetch alert history" }, { status: 500 })
  }
}
