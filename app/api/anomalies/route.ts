// API route for anomaly statistics - proxy to Flask backend

import { flaskApi, transformers } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Get query parameters
    const { searchParams } = new URL(request.url)
    const hours = parseInt(searchParams.get('hours') || '24')
    const severity = searchParams.get('severity') ?? undefined
    
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getAnomalyStats({ hours, severity })
    
    return Response.json(flaskResponse)
  } catch (error) {
    console.error("Error fetching anomaly stats:", error)
    return Response.json({ error: "Failed to fetch anomaly stats" }, { status: 500 })
  }
}
