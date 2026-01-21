// API route for training statistics - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    const flaskResponse = await flaskApi.getTrainingStatistics()
    return Response.json(flaskResponse)
  } catch (flaskError: any) {
    console.warn("Flask backend unavailable for training statistics:", flaskError)
    return Response.json({
      error: "Backend training service unavailable",
      message: "Please ensure the Flask backend is running and classification is enabled"
    }, { status: 503 })
  }
}
