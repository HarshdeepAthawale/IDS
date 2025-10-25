// API route for insider threats summary - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getInsiderThreatsSummary()
    
    return Response.json(flaskResponse)
  } catch (error) {
    console.error("Error fetching insider threats summary:", error)
    return Response.json({ error: "Failed to fetch insider threats summary" }, { status: 500 })
  }
}
