import { io } from 'socket.io-client'

const SOCKET_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'

class SocketService {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 5000
    this.eventListeners = new Map()
  }

  connect() {
    if (this.socket?.connected) {
      console.log('Socket already connected')
      return
    }

    console.log('Connecting to WebSocket server...')
    
    this.socket = io(SOCKET_URL, {
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectInterval,
      timeout: 10000,
    })

    this.setupEventListeners()
  }

  setupEventListeners() {
    if (!this.socket) return

    // Connection events
    this.socket.on('connect', () => {
      console.log('Connected to WebSocket server')
      this.isConnected = true
      this.reconnectAttempts = 0
      this.emit('connect')
    })

    this.socket.on('disconnect', (reason) => {
      console.log('Disconnected from WebSocket server:', reason)
      this.isConnected = false
      this.emit('disconnect', reason)
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.isConnected = false
      this.reconnectAttempts++
      this.emit('error', error)
    })

    // Data events
    this.socket.on('new-alert', (alert) => {
      console.log('New alert received:', alert)
      this.emit('new-alert', alert)
    })

    this.socket.on('stats-update', (stats) => {
      this.emit('stats-update', stats)
    })

    this.socket.on('packet-stream', (packet) => {
      this.emit('packet-stream', packet)
    })

    this.socket.on('alerts-data', (data) => {
      this.emit('alerts-data', data)
    })

    this.socket.on('system-status', (status) => {
      this.emit('system-status', status)
    })

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
      this.emit('error', error)
    })
  }

  // Event subscription methods
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set())
    }
    this.eventListeners.get(event).add(callback)
  }

  off(event, callback) {
    if (this.eventListeners.has(event)) {
      this.eventListeners.get(event).delete(callback)
    }
  }

  emit(event, data) {
    if (this.eventListeners.has(event)) {
      this.eventListeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error)
        }
      })
    }
  }

  // Convenience methods for specific events
  onConnect(callback) {
    this.on('connect', callback)
  }

  onDisconnect(callback) {
    this.on('disconnect', callback)
  }

  onError(callback) {
    this.on('error', callback)
  }

  onNewAlert(callback) {
    this.on('new-alert', callback)
  }

  onStatsUpdate(callback) {
    this.on('stats-update', callback)
  }

  onPacketStream(callback) {
    this.on('packet-stream', callback)
  }

  onAlertsData(callback) {
    this.on('alerts-data', callback)
  }

  onSystemStatus(callback) {
    this.on('system-status', callback)
  }

  // Request methods
  requestStats() {
    if (this.socket?.connected) {
      this.socket.emit('request-stats')
    }
  }

  requestAlerts(options = {}) {
    if (this.socket?.connected) {
      this.socket.emit('request-alerts', options)
    }
  }

  // Connection status
  getConnectionStatus() {
    if (!this.socket) return 'disconnected'
    if (this.socket.connected) return 'connected'
    return 'connecting'
  }

  // Disconnect
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
      this.eventListeners.clear()
      console.log('Disconnected from WebSocket server')
    }
  }

  // Reconnect manually
  reconnect() {
    this.disconnect()
    setTimeout(() => {
      this.connect()
    }, 1000)
  }
}

// Create singleton instance
export const socketService = new SocketService()

export default socketService
