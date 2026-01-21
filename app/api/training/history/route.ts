// API route for training history - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    const flaskResponse = await flaskApi.getTrainingHistory()
    return Response.json(flaskResponse)
  } catch (flaskError: any) {
    console.warn("Flask backend unavailable for training history:", flaskError)
    return Response.json({
      error: "Backend training history service unavailable",
      message: "Please ensure the Flask backend is running"
    }, { status: 503 })
  }
}
