// API route for dashboard statistics - proxy to Flask backend

import { flaskApi, transformers } from "@/lib/flask-api"

export async function GET() {
  try {
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getTrafficStats({ hours: 24 })
    
    // Transform Flask response to frontend format
    const stats = transformers.trafficToDashboardStats(flaskResponse)
    
    return Response.json(stats)
  } catch (error) {
    console.error("Error fetching stats:", error)
    return Response.json({ error: "Failed to fetch stats" }, { status: 500 })
  }
}
