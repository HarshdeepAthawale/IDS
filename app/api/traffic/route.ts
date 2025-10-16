// API route for traffic statistics

import { generateMockTrafficData, generateMockProtocolData } from "@/lib/mock-data"

export async function GET() {
  try {
    // In a real application, this would fetch from your backend/database
    const trafficData = generateMockTrafficData()
    const protocolData = generateMockProtocolData()

    return Response.json({ trafficData, protocolData })
  } catch (error) {
    console.error("Error fetching traffic stats:", error)
    return Response.json({ error: "Failed to fetch traffic stats" }, { status: 500 })
  }
}
