// API route for packet analysis - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    
    // Try to analyze with Flask backend
    try {
      const flaskResponse = await flaskApi.analyzePacket(body)
      
      return Response.json(flaskResponse)
    } catch (flaskError) {
      console.warn("Flask backend unavailable for analysis:", flaskError)
      
      // Fallback response
      return Response.json({
        error: "Backend analysis service unavailable",
        message: "Please ensure the Flask backend is running for packet analysis"
      }, { status: 503 })
    }
  } catch (error) {
    console.error("Error in packet analysis:", error)
    return Response.json({ error: "Failed to analyze packet" }, { status: 500 })
  }
}

export async function GET() {
  try {
    // Try to get model info from Flask backend
    try {
      const flaskResponse = await flaskApi.getModelInfo()
      
      return Response.json(flaskResponse)
    } catch (flaskError) {
      console.warn("Flask backend unavailable for model info:", flaskError)
      
      // Fallback response
      return Response.json({
        error: "Backend analysis service unavailable",
        message: "Please ensure the Flask backend is running for model information"
      }, { status: 503 })
    }
  } catch (error) {
    console.error("Error getting model info:", error)
    return Response.json({ error: "Failed to get model info" }, { status: 500 })
  }
}
