// Proxy GET single PCAP analysis by id to Flask backend

const BACKEND_URL =
  process.env.FLASK_API_URL ||
  process.env.NEXT_PUBLIC_FLASK_API_URL ||
  "http://localhost:3002"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    if (!id) {
      return Response.json({ error: "Analysis id is required" }, { status: 400 })
    }
    const res = await fetch(`${BACKEND_URL}/api/pcap/analyses/${encodeURIComponent(id)}`)
    const data = await res.json().catch(() => ({}))
    return Response.json(data, { status: res.status })
  } catch (error) {
    console.error("PCAP analysis get proxy error:", error)
    return Response.json(
      {
        error: "Failed to fetch PCAP analysis",
        message: error instanceof Error ? error.message : "Proxy error",
      },
      { status: 500 }
    )
  }
}
