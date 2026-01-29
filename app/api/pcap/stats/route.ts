// Proxy GET PCAP detection stats (aggregated from all PCAP analyses) to Flask backend

const BACKEND_URL =
  process.env.FLASK_API_URL ||
  process.env.NEXT_PUBLIC_FLASK_API_URL ||
  "http://localhost:3002"

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/pcap/stats`)
    const data = await res.json().catch(() => ({}))
    return Response.json(data, { status: res.status })
  } catch (error) {
    console.error("PCAP stats proxy error:", error)
    return Response.json(
      {
        error: "Failed to fetch PCAP stats",
        message: error instanceof Error ? error.message : "Proxy error",
      },
      { status: 500 }
    )
  }
}
