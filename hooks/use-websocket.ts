"use client"

import { useWebSocketContext } from "@/contexts/websocket-context"

// Re-export the context hook for backward compatibility
// This hook now uses the shared WebSocket context instead of creating individual connections
export function useWebSocket(options: { room?: string } = {}) {
  // Use the shared WebSocket context
  return useWebSocketContext()
}
