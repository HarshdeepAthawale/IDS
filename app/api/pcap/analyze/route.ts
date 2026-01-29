// Proxy PCAP upload to Flask backend (avoids CORS, single origin)
// Use FLASK_API_URL (server-only) in Docker; fall back to NEXT_PUBLIC_ or localhost

const BACKEND_URL =
  process.env.FLASK_API_URL ||
  process.env.NEXT_PUBLIC_FLASK_API_URL ||
  "http://localhost:3002"

// Allow large uploads and long analysis (up to 100MB PCAP); backend has 5min timeout
const PROXY_TIMEOUT_MS = 6 * 60 * 1000

export async function POST(request: Request) {
  try {
    const formData = await request.formData()
    const file = formData.get("file") as File | null
    const maxPackets = formData.get("max_packets") as string | null

    if (!file || !(file instanceof File)) {
      return Response.json(
        { error: "PCAP file is required under 'file' field" },
        { status: 400 }
      )
    }

    const backendForm = new FormData()
    backendForm.append("file", file)
    if (maxPackets != null && maxPackets !== "") {
      backendForm.append("max_packets", maxPackets)
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), PROXY_TIMEOUT_MS)

    const res = await fetch(`${BACKEND_URL}/api/pcap/analyze`, {
      method: "POST",
      body: backendForm,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    const data = await res.json().catch(() => ({}))
    return Response.json(data, { status: res.status })
  } catch (error) {
    console.error("PCAP analyze proxy error:", error)
    const message =
      error instanceof Error
        ? error.name === "AbortError"
          ? "Request timed out. Try a smaller file or fewer packets (max_packets)."
          : error.message
        : "Proxy error"
    return Response.json(
      {
        error: "Failed to analyze PCAP",
        message,
      },
      { status: 500 }
    )
  }
}
