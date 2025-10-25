// API route for alert summary - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getAlertSummary()
    
    return Response.json(flaskResponse)
  } catch (error) {
    console.error("Error fetching alert summary:", error)
    return Response.json({ error: "Failed to fetch alert summary" }, { status: 500 })
  }
}
