// API route for confusion matrix - proxy to Flask backend

import { flaskApi } from "@/lib/flask-api"

export async function GET() {
  try {
    const flaskResponse = await flaskApi.getConfusionMatrix()
    return Response.json(flaskResponse)
  } catch (flaskError: any) {
    console.warn("Flask backend unavailable for confusion matrix:", flaskError)
    return Response.json({
      error: "Backend confusion matrix service unavailable",
      message: "Please ensure the Flask backend is running and model is trained"
    }, { status: 503 })
  }
}
