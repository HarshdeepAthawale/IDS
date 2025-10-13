import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    
    // Handle specific error cases
    if (error.code === 'ECONNREFUSED') {
      throw new Error('Backend server is not running')
    } else if (error.response?.status === 404) {
      throw new Error('API endpoint not found')
    } else if (error.response?.status >= 500) {
      throw new Error('Server error occurred')
    }
    
    throw error
  }
)

export const apiService = {
  // Health check
  async healthCheck() {
    const response = await api.get('/health')
    return response.data
  },

  // Get alerts with pagination and filtering
  async getAlerts(options = {}) {
    const params = new URLSearchParams()
    
    if (options.page) params.append('page', options.page)
    if (options.limit) params.append('limit', options.limit)
    if (options.severity) params.append('severity', options.severity)
    if (options.type) params.append('type', options.type)
    if (options.source_ip) params.append('source_ip', options.source_ip)
    
    const response = await api.get(`/api/alerts?${params.toString()}`)
    return response.data
  },

  // Get real-time statistics
  async getStats() {
    const response = await api.get('/api/stats')
    return response.data
  },

  // Get packet capture status
  async getPacketStatus() {
    const response = await api.get('/api/packets/status')
    return response.data
  },

  // Start packet capture
  async startPacketCapture(interfaceName = null, filter = '') {
    const response = await api.post('/api/packets/start', {
      interface: interfaceName,
      filter: filter
    })
    return response.data
  },

  // Stop packet capture
  async stopPacketCapture() {
    const response = await api.post('/api/packets/stop')
    return response.data
  },

  // Get available network interfaces
  async getInterfaces() {
    const response = await api.get('/api/packets/interfaces')
    return response.data
  },

  // Get IDS engine status
  async getIDSStatus() {
    const response = await api.get('/api/ids/status')
    return response.data
  },

  // Update IDS configuration
  async updateIDSConfig(config) {
    const response = await api.post('/api/ids/config', config)
    return response.data
  },

  // Reset IDS tracking data
  async resetIDSTracking() {
    const response = await api.post('/api/ids/reset')
    return response.data
  },

  // Test packet injection (for testing)
  async injectTestPacket(packet) {
    const response = await api.post('/api/packets/inject', packet)
    return response.data
  },

  // Get alert by ID
  async getAlertById(alertId) {
    const response = await api.get(`/api/alerts/${alertId}`)
    return response.data
  },

  // Mark alert as resolved
  async resolveAlert(alertId) {
    const response = await api.patch(`/api/alerts/${alertId}/resolve`)
    return response.data
  },

  // Get system information
  async getSystemInfo() {
    const response = await api.get('/api/system/info')
    return response.data
  }
}

export default apiService
