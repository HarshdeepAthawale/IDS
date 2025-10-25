// API route for system information - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getSystemInfo()
    
    return Response.json(flaskResponse)
  } catch (error) {
    console.error("Error fetching system info:", error)
    return Response.json({ error: "Failed to fetch system info" }, { status: 500 })
  }
}
