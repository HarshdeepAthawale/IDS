'use client'

import { useState, useEffect } from 'react'
import Header from '../components/Header'
import AlertTable from '../components/AlertTable'
import PacketGraph from '../components/PacketGraph'
import StatsCard from '../components/StatsCard'
import LiveIndicator from '../components/LiveIndicator'
import SystemStatus from '../components/SystemStatus'
import PacketFlow from '../components/PacketFlow'
import AlertFilters from '../components/AlertFilters'
import ConnectionStatus from '../components/ConnectionStatus'
import { ErrorNotificationContainer } from '../components/ErrorNotification'
import { socketService } from '../lib/socket'
import { apiService } from '../lib/api'
import { dataManager } from '../lib/dataManager'
import { connectionManager } from '../lib/connectionManager'
import { ErrorHandler } from '../lib/errorHandler'

export default function Dashboard() {
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState({
    packets_per_sec: 0,
    total_intrusions: 0,
    top_suspicious_ips: [],
    traffic_mb_per_sec: 0
  })
  const [packetData, setPacketData] = useState([])
  const [packetFlows, setPacketFlows] = useState([])
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [alertFilters, setAlertFilters] = useState({})
  const [notifications, setNotifications] = useState([])
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    // Initialize services
    initializeServices()
    
    // Set up comprehensive event listeners
    setupEventListeners()
    
    // Load initial data
    loadInitialData()

    // Cleanup on unmount
    return () => {
      cleanup()
    }
  }, [])

  const initializeServices = () => {
    // Initialize socket connection
    socketService.connect()
    
    // Start connection manager
    connectionManager.startHealthChecks()
  }

  const setupEventListeners = () => {
    // Socket connection events
    socketService.onConnect(() => {
      setConnectionStatus('online')
      console.log('Connected to WebSocket server')
      addNotification('success', 'Connected to real-time updates')
    })

    socketService.onDisconnect((reason) => {
      setConnectionStatus('offline')
      console.log('Disconnected from WebSocket server:', reason)
      addNotification('warning', 'Disconnected from real-time updates', reason)
    })

    socketService.on('connection-state', (data) => {
      setConnectionStatus(data.state)
    })

    socketService.onError((error) => {
      setConnectionStatus('offline')
      addNotification('error', 'Connection error', error.message)
      console.error('WebSocket error:', error)
    })

    // Data events with caching integration
    socketService.onNewAlert((alert) => {
      setAlerts(prev => [alert, ...prev].slice(0, 100)) // Keep last 100 alerts
      console.log('New alert received:', alert)
    })

    socketService.onStatsUpdate((newStats) => {
      setStats(newStats)
      
      // Update packet data for graph
      setPacketData(prev => {
        const newData = [...prev, {
          time: new Date().toLocaleTimeString(),
          packets: newStats.packets_per_sec,
          traffic: newStats.traffic_mb_per_sec
        }].slice(-60) // Keep last 60 data points
        return newData
      })
    })

    socketService.onPacketStream((packet) => {
      console.log('Packet stream received:', packet)
      // Update packet flows for visualization
      setPacketFlows(prev => {
        const newFlows = [...prev, packet].slice(-100) // Keep last 100 packets
        return newFlows
      })
    })

    // Data manager events
    dataManager.on('sync', (data) => {
      console.log('Data synced:', data.type, data.source)
    })

    // Connection manager events
    connectionManager.on('network', (data) => {
      setIsOnline(data.status === 'online')
      if (data.status === 'offline') {
        addNotification('error', 'Network connection lost')
      } else if (data.status === 'online') {
        addNotification('success', 'Network connection restored')
      }
    })

    connectionManager.on('health', (data) => {
      if (data.status === 'unhealthy') {
        addNotification('warning', 'Backend health check failed', data.error)
      }
    })

    connectionManager.on('reconnection', (data) => {
      if (data.status === 'attempting') {
        addNotification('info', `Attempting reconnection ${data.attempt}/${data.maxReconnectAttempts}`)
      } else if (data.status === 'success') {
        addNotification('success', 'Reconnection successful')
      } else if (data.status === 'failed') {
        addNotification('error', 'Reconnection failed', 'Please refresh the page')
      }
    })
  }

  const cleanup = () => {
    socketService.disconnect()
    connectionManager.stopHealthChecks()
    dataManager.destroy()
  }

  const loadInitialData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Try to load cached data first
      const cachedData = dataManager.getCachedData()
      if (cachedData.alerts.length > 0) {
        setAlerts(cachedData.alerts)
      }
      if (cachedData.stats.packets_per_sec > 0) {
        setStats(cachedData.stats)
      }

      // Load fresh data
      const dashboardData = await apiService.getDashboardData()
      
      if (dashboardData.alerts) {
        setAlerts(dashboardData.alerts.alerts || [])
      }
      
      if (dashboardData.stats) {
        setStats(dashboardData.stats)
      }

      // Handle any errors from individual requests
      if (dashboardData.errors.length > 0) {
        dashboardData.errors.forEach(error => {
          const errorInfo = ErrorHandler.handle(error, 'Initial Data Load')
          addNotification('error', errorInfo.message, errorInfo.suggestion)
        })
      }

      setLoading(false)
    } catch (err) {
      console.error('Error loading initial data:', err)
      const errorInfo = ErrorHandler.handle(err, 'Initial Data Load')
      setError(errorInfo.message)
      addNotification('error', errorInfo.message, errorInfo.suggestion)
      setLoading(false)
    }
  }

  const refreshData = () => {
    loadInitialData()
  }

  const handleAlertFilterChange = (filters) => {
    setAlertFilters(filters)
  }

  const addNotification = (type, message, suggestion = null) => {
    const notification = {
      id: Date.now().toString(),
      type,
      message,
      suggestion,
      severity: type === 'error' ? 'high' : type === 'warning' ? 'medium' : 'low',
      timestamp: new Date().toISOString(),
      dismissed: false
    }
    
    setNotifications(prev => [notification, ...prev].slice(0, 5)) // Keep last 5 notifications
  }

  const dismissNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const handleRetry = () => {
    loadInitialData()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-dark-accent mx-auto mb-4"></div>
          <p className="text-dark-text-muted">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dark-bg">
      {/* Error Notifications */}
      <ErrorNotificationContainer 
        errors={notifications}
        onDismissError={dismissNotification}
      />
      
      <Header 
        connectionStatus={connectionStatus}
        onRefresh={refreshData}
      />
      
      <main className="container mx-auto px-4 py-6">
        {/* Global Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-800/30 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-red-400 font-medium">{error}</p>
                <button 
                  onClick={handleRetry}
                  className="mt-2 text-sm text-red-300 hover:text-red-200 mr-4"
                >
                  Retry
                </button>
                <button 
                  onClick={() => setError(null)}
                  className="mt-2 text-sm text-red-300 hover:text-red-200"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Network Status Warning */}
        {!isOnline && (
          <div className="mb-6 p-4 bg-yellow-900/20 border border-yellow-800/30 rounded-lg">
            <div className="flex items-center space-x-2">
              <span className="text-yellow-400">⚠️</span>
              <p className="text-yellow-400">You are currently offline. Some features may not work properly.</p>
            </div>
          </div>
        )}

        {/* Live Status Bar */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <LiveIndicator status={connectionStatus} />
            <div>
              <h1 className="text-2xl font-bold text-dark-text">IDS Dashboard</h1>
              <p className="text-dark-text-muted">Real-time network monitoring</p>
            </div>
          </div>
          <button
            onClick={refreshData}
            className="btn-secondary flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Packets/sec"
            value={stats.packets_per_sec}
            unit="pkt/s"
            icon="📊"
            color="blue"
          />
          <StatsCard
            title="Total Intrusions"
            value={stats.total_intrusions}
            unit="alerts"
            icon="🚨"
            color="red"
          />
          <StatsCard
            title="Traffic Rate"
            value={stats.traffic_mb_per_sec}
            unit="MB/s"
            icon="📈"
            color="green"
          />
          <StatsCard
            title="Suspicious IPs"
            value={stats.top_suspicious_ips?.length || 0}
            unit="IPs"
            icon="🔍"
            color="yellow"
          />
        </div>

        {/* System Status and Connection Info */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
          <div className="lg:col-span-3">
            <SystemStatus />
          </div>
          <div>
            <ConnectionStatus />
          </div>
        </div>

        {/* Charts and Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Packet Rate Chart */}
          <div className="lg:col-span-2 card">
            <h2 className="text-xl font-semibold mb-4 text-dark-text">Packet Rate</h2>
            <PacketGraph data={packetData} />
          </div>

          {/* Packet Flows */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4 text-dark-text">Active Flows</h2>
            <PacketFlow packets={packetFlows} />
          </div>
        </div>

        {/* Top Suspicious IPs */}
        <div className="card mb-8">
          <h2 className="text-xl font-semibold mb-4 text-dark-text">Top Suspicious IPs</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.top_suspicious_ips?.length > 0 ? (
              stats.top_suspicious_ips.map((ip, index) => (
                <div key={ip.ip} className="flex items-center justify-between p-3 bg-dark-surface rounded-lg border border-dark-border">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-mono text-dark-text-muted bg-dark-card px-2 py-1 rounded">#{index + 1}</span>
                    <span className="font-mono text-dark-text">{ip.ip}</span>
                  </div>
                  <span className="text-sm font-semibold text-red-400">{ip.count} alerts</span>
                </div>
              ))
            ) : (
              <div className="col-span-full text-center py-8">
                <div className="text-4xl mb-2">🛡️</div>
                <p className="text-dark-text-muted">No suspicious IPs detected</p>
              </div>
            )}
          </div>
        </div>

        {/* Alert Filters */}
        <AlertFilters 
          onFilterChange={handleAlertFilterChange}
          currentFilters={alertFilters}
        />

        {/* Alerts Table */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-dark-text">Recent Alerts</h2>
            <span className="text-sm text-dark-text-muted">
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
            </span>
          </div>
          <AlertTable 
            alerts={alerts} 
            onFilterChange={handleAlertFilterChange}
            currentFilters={alertFilters}
          />
        </div>
      </main>
    </div>
  )
}
