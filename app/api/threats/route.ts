// API route for insider threats

import { generateMockInsiderThreats } from "@/lib/mock-data"

export async function GET() {
  try {
    // In a real application, this would fetch from your backend/database
    const threats = generateMockInsiderThreats()

    return Response.json(threats)
  } catch (error) {
    console.error("Error fetching insider threats:", error)
    return Response.json({ error: "Failed to fetch insider threats" }, { status: 500 })
  }
}
