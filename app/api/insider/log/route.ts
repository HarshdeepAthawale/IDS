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
      console.error("Flask backend unavailable for insider threat logging:", flaskError)
      
      // Return proper error, no mock response
      return Response.json({
        error: "Backend service unavailable",
        message: "Flask backend must be running for insider threat logging"
      }, { status: 503 })
    }
  } catch (error) {
    console.error("Error logging insider threat:", error)
    return Response.json({ error: "Failed to log insider threat" }, { status: 500 })
  }
}
