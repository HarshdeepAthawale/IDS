// API route for model evaluation - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    const flaskResponse = await flaskApi.evaluateModel()
    return Response.json(flaskResponse)
  } catch (flaskError: any) {
    console.warn("Flask backend unavailable for evaluation:", flaskError)
    return Response.json({
      error: "Backend evaluation service unavailable",
      message: "Please ensure the Flask backend is running and model is trained"
    }, { status: 503 })
  }
}
