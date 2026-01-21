// API route for model metrics - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    const flaskResponse = await flaskApi.getModelMetrics()
    return Response.json(flaskResponse)
  } catch (flaskError: any) {
    console.warn("Flask backend unavailable for metrics:", flaskError)
    return Response.json({
      error: "Backend metrics service unavailable",
      message: "Please ensure the Flask backend is running"
    }, { status: 503 })
  }
}
