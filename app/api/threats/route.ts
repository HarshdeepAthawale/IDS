// API route for insider threats - proxy to Flask backend

import { flaskApi, transformers } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Get query parameters
    const { searchParams } = new URL(request.url)
    const params = Object.fromEntries(searchParams.entries())
    
    // Fetch from Flask backend
    const flaskResponse = await flaskApi.getInsiderThreats(params)
    
    // Transform Flask response to frontend format
    const threats = flaskResponse.activities.map(transformers.userActivityToFrontend)
    
    return Response.json({
      threats,
      total: flaskResponse.total,
      summary: flaskResponse.summary,
      riskAssessment: flaskResponse.risk_assessment
    })
  } catch (error) {
    console.error("Error fetching insider threats:", error)
    return Response.json({ error: "Failed to fetch insider threats" }, { status: 500 })
  }
}
