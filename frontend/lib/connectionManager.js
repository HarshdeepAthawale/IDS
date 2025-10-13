// Connection management and health monitoring
export class ConnectionManager {
  constructor() {
    this.isOnline = navigator.onLine
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.maxReconnectDelay = 30000
    this.healthCheckInterval = null
    this.listeners = new Map()
    
    this.setupNetworkListeners()
  }
  
  setupNetworkListeners() {
    // Monitor network connectivity
    window.addEventListener('online', () => {
      this.isOnline = true
      this.emit('network', { status: 'online' })
      console.log('Network connection restored')
    })
    
    window.addEventListener('offline', () => {
      this.isOnline = false
      this.emit('network', { status: 'offline' })
      console.log('Network connection lost')
    })
  }
  
  // Event subscription system
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
  }
  
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback)
    }
  }
  
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in connection manager listener for ${event}:`, error)
        }
      })
    }
  }
  
  // Health check methods
  async checkBackendHealth() {
    try {
      const response = await fetch('/health', {
        method: 'GET',
        timeout: 5000
      })
      
      if (response.ok) {
        const data = await response.json()
        this.emit('health', { status: 'healthy', data })
        return { status: 'healthy', data }
      } else {
        this.emit('health', { status: 'unhealthy', error: 'HTTP ' + response.status })
        return { status: 'unhealthy', error: 'HTTP ' + response.status }
      }
    } catch (error) {
      this.emit('health', { status: 'unhealthy', error: error.message })
      return { status: 'unhealthy', error: error.message }
    }
  }
  
  // Auto-reconnection logic
  async attemptReconnection(connectionType = 'websocket') {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnection attempts reached')
      this.emit('reconnection', { 
        status: 'failed', 
        attempts: this.reconnectAttempts 
      })
      return false
    }
    
    this.reconnectAttempts++
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    )
    
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`)
    
    this.emit('reconnection', { 
      status: 'attempting', 
      attempt: this.reconnectAttempts,
      delay 
    })
    
    return new Promise((resolve) => {
      setTimeout(async () => {
        try {
          const healthCheck = await this.checkBackendHealth()
          if (healthCheck.status === 'healthy') {
            this.reconnectAttempts = 0
            this.emit('reconnection', { 
              status: 'success', 
              attempt: this.reconnectAttempts 
            })
            resolve(true)
          } else {
            resolve(await this.attemptReconnection(connectionType))
          }
        } catch (error) {
          resolve(await this.attemptReconnection(connectionType))
        }
      }, delay)
    })
  }
  
  // Start periodic health checks
  startHealthChecks(interval = 30000) {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
    }
    
    this.healthCheckInterval = setInterval(async () => {
      await this.checkBackendHealth()
    }, interval)
  }
  
  // Stop health checks
  stopHealthChecks() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
      this.healthCheckInterval = null
    }
  }
  
  // Get connection status
  getStatus() {
    return {
      isOnline: this.isOnline,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      isHealthChecking: !!this.healthCheckInterval
    }
  }
  
  // Reset reconnection attempts
  resetReconnectAttempts() {
    this.reconnectAttempts = 0
  }
  
  // Cleanup
  destroy() {
    this.stopHealthChecks()
    this.listeners.clear()
    window.removeEventListener('online', () => {})
    window.removeEventListener('offline', () => {})
  }
}

// Create singleton instance
export const connectionManager = new ConnectionManager()
