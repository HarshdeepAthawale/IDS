// API route for real-time statistics - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    // Fetch real-time stats from Flask backend (from in-memory cache)
    const flaskResponse = await flaskApi.getRealtimeStats()
    
    return Response.json(flaskResponse)
  } catch (error) {
    console.error("Error fetching real-time stats:", error)
    return Response.json({ 
      error: "Failed to fetch real-time stats",
      message: error instanceof Error ? error.message : "Backend may be unavailable or no packets captured yet"
    }, { status: 500 })
  }
}