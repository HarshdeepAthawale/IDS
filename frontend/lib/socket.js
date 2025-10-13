import { io } from 'socket.io-client'
import { connectionManager } from './connectionManager'
import { dataManager } from './dataManager'
import { ErrorHandler } from './errorHandler'

const SOCKET_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'

class SocketService {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 5000
    this.eventListeners = new Map()
    this.connectionState = 'disconnected'
    this.lastConnectedAt = null
    this.heartbeatInterval = null
  }

  connect() {
    if (this.socket?.connected) {
      console.log('Socket already connected')
      return
    }

    console.log('Connecting to WebSocket server...')
    this.connectionState = 'connecting'
    this.emit('connection-state', { state: 'connecting' })
    
    this.socket = io(SOCKET_URL, {
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectInterval,
      timeout: 10000,
      forceNew: true
    })

    this.setupEventListeners()
    this.startHeartbeat()
  }

  setupEventListeners() {
    if (!this.socket) return

    // Connection events
    this.socket.on('connect', () => {
      console.log('Connected to WebSocket server')
      this.isConnected = true
      this.connectionState = 'connected'
      this.lastConnectedAt = Date.now()
      this.reconnectAttempts = 0
      connectionManager.resetReconnectAttempts()
      
      this.emit('connect')
      this.emit('connection-state', { state: 'connected', timestamp: this.lastConnectedAt })
      
      // Request initial data
      this.requestStats()
      this.requestAlerts()
    })

    this.socket.on('disconnect', (reason) => {
      console.log('Disconnected from WebSocket server:', reason)
      this.isConnected = false
      this.connectionState = 'disconnected'
      this.stopHeartbeat()
      
      this.emit('disconnect', reason)
      this.emit('connection-state', { state: 'disconnected', reason })
      
      // Attempt reconnection if not intentional
      if (reason !== 'io client disconnect') {
        this.attemptReconnection()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.isConnected = false
      this.connectionState = 'error'
      this.reconnectAttempts++
      
      const errorInfo = ErrorHandler.handle(error, 'WebSocket Connection')
      this.emit('error', errorInfo)
      this.emit('connection-state', { state: 'error', error: errorInfo })
    })

    // Data events with data management integration
    this.socket.on('new-alert', (alert) => {
      console.log('New alert received:', alert)
      
      // Validate alert data
      if (dataManager.validateAlert(alert)) {
        const currentAlerts = dataManager.getAlerts()
        const updatedAlerts = [alert, ...currentAlerts].slice(0, 1000) // Keep last 1000 alerts
        dataManager.updateAlerts(updatedAlerts, 'websocket')
      }
      
      this.emit('new-alert', alert)
    })

    this.socket.on('stats-update', (stats) => {
      // Validate stats data
      if (dataManager.validateStats(stats)) {
        dataManager.updateStats(stats, 'websocket')
      }
      
      this.emit('stats-update', stats)
    })

    this.socket.on('packet-stream', (packet) => {
      const currentPackets = dataManager.getPackets()
      const updatedPackets = [...currentPackets, packet].slice(-100) // Keep last 100 packets
      dataManager.updatePackets(updatedPackets, 'websocket')
      
      this.emit('packet-stream', packet)
    })

    this.socket.on('alerts-data', (data) => {
      if (data.alerts && Array.isArray(data.alerts)) {
        dataManager.updateAlerts(data.alerts, 'websocket')
      }
      
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
    return this.connectionState
  }
  
  // Get detailed connection info
  getConnectionInfo() {
    return {
      state: this.connectionState,
      isConnected: this.isConnected,
      lastConnectedAt: this.lastConnectedAt,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      uptime: this.lastConnectedAt ? Date.now() - this.lastConnectedAt : 0
    }
  }
  
  // Heartbeat system
  startHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
    }
    
    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit('ping')
      }
    }, 30000) // Send ping every 30 seconds
  }
  
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }
  
  // Enhanced reconnection logic
  async attemptReconnection() {
    try {
      const success = await connectionManager.attemptReconnection('websocket')
      if (success) {
        this.connect()
      }
    } catch (error) {
      console.error('Reconnection failed:', error)
    }
  }

  // Disconnect
  disconnect() {
    if (this.socket) {
      this.stopHeartbeat()
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
      this.connectionState = 'disconnected'
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
  
  // Get cached data
  getCachedData() {
    return {
      alerts: dataManager.getAlerts(),
      stats: dataManager.getStats(),
      packets: dataManager.getPackets()
    }
  }
}

// Create singleton instance
export const socketService = new SocketService()

export default socketService
