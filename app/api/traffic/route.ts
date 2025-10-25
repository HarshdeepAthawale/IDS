// API route for traffic statistics - proxy to Flask backend

import { flaskApi, transformers } from "@/lib/flask-api"

export async function GET(request: Request) {
  try {
    // Get query parameters
    const { searchParams } = new URL(request.url)
    const hours = parseInt(searchParams.get('hours') || '24')
    
    // Fetch from Flask backend
    const [trafficResponse, protocolResponse] = await Promise.all([
      flaskApi.getTrafficStats({ hours, limit: 24 }),
      flaskApi.getProtocolStats({ hours, limit: 10 })
    ])
    
    // Transform Flask responses to frontend format
    const trafficData = transformers.trafficStatsToFrontend(trafficResponse.historical_data)
    const protocolData = protocolResponse.protocol_distribution 
      ? transformers.protocolStatsToFrontend(protocolResponse.protocol_distribution)
      : []
    
    return Response.json({ 
      trafficData, 
      protocolData,
      summary: trafficResponse.summary,
      current: trafficResponse.current_stats
    })
  } catch (error) {
    console.error("Error fetching traffic stats:", error)
    return Response.json({ error: "Failed to fetch traffic stats" }, { status: 500 })
  }
}
