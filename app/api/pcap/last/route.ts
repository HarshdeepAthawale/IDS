// Proxy GET last PCAP analysis to Flask backend

const BACKEND_URL =
  process.env.FLASK_API_URL ||
  process.env.NEXT_PUBLIC_FLASK_API_URL ||
  "http://localhost:3002"

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/pcap/last`)
    const data = await res.json().catch(() => ({}))
    return Response.json(data, { status: res.status })
  } catch (error) {
    console.error("PCAP last proxy error:", error)
    return Response.json(
      {
        error: "Failed to fetch last PCAP analysis",
        message: error instanceof Error ? error.message : "Proxy error",
      },
      { status: 500 }
    )
  }
}
