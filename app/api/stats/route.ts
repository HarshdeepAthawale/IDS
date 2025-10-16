// API route for dashboard statistics

export async function GET() {
  try {
    // In a real application, this would fetch from your backend/database
    const stats = {
      totalAlerts: 1247,
      criticalAlerts: 23,
      activeConnections: 156,
      totalPackets: 2847392,
    }

    return Response.json(stats)
  } catch (error) {
    console.error("Error fetching stats:", error)
    return Response.json({ error: "Failed to fetch stats" }, { status: 500 })
  }
}
