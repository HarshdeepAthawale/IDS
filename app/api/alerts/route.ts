// API route for alerts

import { generateMockAlerts } from "@/lib/mock-data"

export async function GET() {
  try {
    // In a real application, this would fetch from your backend/database
    const alerts = generateMockAlerts()

    return Response.json(alerts)
  } catch (error) {
    console.error("Error fetching alerts:", error)
    return Response.json({ error: "Failed to fetch alerts" }, { status: 500 })
  }
}
