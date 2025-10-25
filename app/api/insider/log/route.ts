// API route for logging insider threats - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    
    // Try to send to Flask backend
    try {
      const flaskResponse = await flaskApi.logInsiderThreat(body)
      
      return Response.json(flaskResponse)
    } catch (flaskError) {
      console.warn("Flask backend unavailable, simulating response:", flaskError)
      
      // Fallback to mock response
      return Response.json({
        message: "Threat logged successfully (mock response)",
        threat_id: Math.floor(Math.random() * 1000) + 1
      })
    }
  } catch (error) {
    console.error("Error logging insider threat:", error)
    return Response.json({ error: "Failed to log insider threat" }, { status: 500 })
  }
}
