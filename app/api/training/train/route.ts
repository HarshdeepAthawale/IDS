// API route for model training - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const flaskResponse = await flaskApi.trainModel(body)
    return Response.json(flaskResponse)
  } catch (flaskError: any) {
    console.warn("Flask backend unavailable for training:", flaskError)
    return Response.json({
      error: "Backend training service unavailable",
      message: flaskError.message || "Please ensure the Flask backend is running and classification is enabled"
    }, { status: 503 })
  }
}
