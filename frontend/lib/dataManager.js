// Centralized data management and caching
export class DataManager {
  constructor() {
    this.cache = new Map()
    this.cacheTimeout = 5 * 60 * 1000 // 5 minutes default
    this.listeners = new Map()
    this.pendingRequests = new Map()
  }
  
  // Cache management
  setCache(key, data, timeout = this.cacheTimeout) {
    const cacheItem = {
      data,
      timestamp: Date.now(),
      timeout
    }
    this.cache.set(key, cacheItem)
    this.emit('cache', { action: 'set', key, data })
  }
  
  getCache(key) {
    const cacheItem = this.cache.get(key)
    if (!cacheItem) return null
    
    const isExpired = Date.now() - cacheItem.timestamp > cacheItem.timeout
    if (isExpired) {
      this.cache.delete(key)
      this.emit('cache', { action: 'expired', key })
      return null
    }
    
    return cacheItem.data
  }
  
  clearCache(key = null) {
    if (key) {
      this.cache.delete(key)
      this.emit('cache', { action: 'clear', key })
    } else {
      this.cache.clear()
      this.emit('cache', { action: 'clear', key: 'all' })
    }
  }
  
  // Request deduplication
  async makeRequest(key, requestFn, options = {}) {
    // Check if request is already pending
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key)
    }
    
    // Check cache first
    const cachedData = this.getCache(key)
    if (cachedData && !options.forceRefresh) {
      return cachedData
    }
    
    // Create new request
    const requestPromise = requestFn()
      .then(data => {
        // Cache successful response
        this.setCache(key, data, options.cacheTimeout)
        this.pendingRequests.delete(key)
        this.emit('request', { action: 'success', key, data })
        return data
      })
      .catch(error => {
        this.pendingRequests.delete(key)
        this.emit('request', { action: 'error', key, error })
        throw error
      })
    
    this.pendingRequests.set(key, requestPromise)
    return requestPromise
  }
  
  // Data synchronization
  syncData(type, data, options = {}) {
    const syncKey = `sync_${type}_${Date.now()}`
    
    // Update cache
    this.setCache(type, data, options.cacheTimeout)
    
    // Emit sync event
    this.emit('sync', { 
      type, 
      data, 
      key: syncKey,
      timestamp: Date.now(),
      source: options.source || 'unknown'
    })
    
    return syncKey
  }
  
  // Event system
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
          console.error(`Error in data manager listener for ${event}:`, error)
        }
      })
    }
  }
  
  // Specific data management methods
  updateAlerts(alerts, source = 'api') {
    this.syncData('alerts', alerts, { source })
  }
  
  updateStats(stats, source = 'websocket') {
    this.syncData('stats', stats, { source })
  }
  
  updatePackets(packets, source = 'websocket') {
    this.syncData('packets', packets, { source })
  }
  
  // Get current data
  getAlerts() {
    return this.getCache('alerts') || []
  }
  
  getStats() {
    return this.getCache('stats') || {
      packets_per_sec: 0,
      total_intrusions: 0,
      top_suspicious_ips: [],
      traffic_mb_per_sec: 0
    }
  }
  
  getPackets() {
    return this.getCache('packets') || []
  }
  
  // Data validation
  validateAlert(alert) {
    const required = ['id', 'timestamp', 'type', 'severity', 'source_ip']
    return required.every(field => alert[field] !== undefined)
  }
  
  validateStats(stats) {
    const required = ['packets_per_sec', 'total_intrusions', 'traffic_mb_per_sec']
    return required.every(field => typeof stats[field] === 'number')
  }
  
  // Cleanup expired cache
  cleanup() {
    const now = Date.now()
    for (const [key, cacheItem] of this.cache.entries()) {
      if (now - cacheItem.timestamp > cacheItem.timeout) {
        this.cache.delete(key)
      }
    }
  }
  
  // Get cache statistics
  getCacheStats() {
    const now = Date.now()
    let expired = 0
    let active = 0
    
    for (const [key, cacheItem] of this.cache.entries()) {
      if (now - cacheItem.timestamp > cacheItem.timeout) {
        expired++
      } else {
        active++
      }
    }
    
    return {
      total: this.cache.size,
      active,
      expired,
      pendingRequests: this.pendingRequests.size
    }
  }
  
  // Destroy manager
  destroy() {
    this.cache.clear()
    this.pendingRequests.clear()
    this.listeners.clear()
  }
}

// Create singleton instance
export const dataManager = new DataManager()
