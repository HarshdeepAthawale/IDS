"use client"

import { WebSocketProvider } from "@/contexts/websocket-context"

export function WebSocketProviderWrapper({ children }: { children: React.ReactNode }) {
  return <WebSocketProvider>{children}</WebSocketProvider>
}
