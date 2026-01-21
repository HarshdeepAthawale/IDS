"use client"

import React, { createContext, useContext, useEffect, useRef, useState, useCallback, ReactNode } from "react"
import { io, Socket } from "socket.io-client"

interface WebSocketContextType {
  socket: Socket | null
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  connect: () => void
  disconnect: () => void
  emit: (event: string, data?: any) => void
  on: (event: string, callback: (data: any) => void) => void
  off: (event: string, callback?: (data: any) => void) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
  url?: string
  room?: string
  autoConnect?: boolean
}

export function WebSocketProvider({ 
  children, 
  url = 'http://localhost:3002',
  room = 'dashboard',
  autoConnect = true 
}: WebSocketProviderProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<Socket | null>(null)
  const listenersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map())
  const shouldConnectRef = useRef<boolean>(autoConnect)
  const urlRef = useRef<string>(url)
  const roomRef = useRef<string>(room)
  
  // Update refs when props change
  urlRef.current = url
  roomRef.current = room
  shouldConnectRef.current = autoConnect

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return
    }

    try {
      setIsConnecting(true)
      setError(null)

      const socket = io(urlRef.current, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5
      })

      socketRef.current = socket

      socket.on('connect', () => {
        console.log('WebSocket Context: Connected')
        setIsConnected(true)
        setIsConnecting(false)
        setError(null)
        
        if (roomRef.current) {
          socket.emit('join_room', { room: roomRef.current })
        }

        // Re-register all existing listeners
        listenersRef.current.forEach((callbacks, event) => {
          callbacks.forEach(callback => {
            socket.on(event, callback)
          })
        })
      })

      socket.on('connected', (data: any) => {
        console.log('WebSocket Context: Server confirmed connection', data)
      })

      socket.on('disconnect', () => {
        console.log('WebSocket Context: Disconnected')
        setIsConnected(false)
        setIsConnecting(false)
      })

      socket.on('connect_error', (err: Error) => {
        console.error('WebSocket Context: Connection error', err)
        setError('Failed to connect to real-time server. Backend may not be running.')
        setIsConnected(false)
        setIsConnecting(false)
      })

    } catch (err) {
      console.error('WebSocket Context: Error creating connection', err)
      setError('Failed to create WebSocket connection')
      setIsConnecting(false)
    }
  }, []) // No dependencies - uses refs

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      if (roomRef.current) {
        socketRef.current.emit('leave_room', { room: roomRef.current })
      }
      socketRef.current.disconnect()
      socketRef.current = null
    }
    setIsConnected(false)
    setIsConnecting(false)
  }, []) // No dependencies - uses refs

  const emit = useCallback((event: string, data?: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data)
    } else {
      console.warn(`WebSocket Context: Cannot emit ${event} - not connected`)
    }
  }, [])

  const on = useCallback((event: string, callback: (data: any) => void) => {
    if (!listenersRef.current.has(event)) {
      listenersRef.current.set(event, new Set())
    }
    listenersRef.current.get(event)!.add(callback)

    if (socketRef.current?.connected) {
      socketRef.current.on(event, callback)
    }
  }, [])

  const off = useCallback((event: string, callback?: (data: any) => void) => {
    if (callback) {
      listenersRef.current.get(event)?.delete(callback)
      if (socketRef.current?.connected) {
        socketRef.current.off(event, callback)
      }
    } else {
      listenersRef.current.delete(event)
      if (socketRef.current?.connected) {
        socketRef.current.off(event)
      }
    }
  }, [])

  useEffect(() => {
    if (shouldConnectRef.current) {
      connect()
    }

    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run on mount/unmount - connect/disconnect are stable

  const value: WebSocketContextType = {
    socket: socketRef.current,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    emit,
    on,
    off
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider')
  }
  return context
}
