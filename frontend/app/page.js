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
import { socketService } from '../lib/socket'
import { apiService } from '../lib/api'

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

  useEffect(() => {
    // Initialize socket connection
    socketService.connect()
    
    // Set up event listeners
    socketService.onConnect(() => {
      setConnectionStatus('online')
      console.log('Connected to WebSocket server')
    })

    socketService.onDisconnect(() => {
      setConnectionStatus('offline')
      console.log('Disconnected from WebSocket server')
    })

    socketService.onError((error) => {
      setConnectionStatus('offline')
      setError(`Connection error: ${error.message}`)
      console.error('WebSocket error:', error)
    })

    // Listen for real-time updates
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

    // Load initial data
    loadInitialData()

    // Cleanup on unmount
    return () => {
      socketService.disconnect()
    }
  }, [])

  const loadInitialData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load initial alerts
      const alertsData = await apiService.getAlerts({ limit: 50 })
      setAlerts(alertsData.alerts || [])

      // Load initial stats
      const statsData = await apiService.getStats()
      setStats(statsData)

      setLoading(false)
    } catch (err) {
      console.error('Error loading initial data:', err)
      setError(`Failed to load data: ${err.message}`)
      setLoading(false)
    }
  }

  const refreshData = () => {
    loadInitialData()
  }

  const handleAlertFilterChange = (filters) => {
    setAlertFilters(filters)
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
      <Header 
        connectionStatus={connectionStatus}
        onRefresh={refreshData}
      />
      
      <main className="container mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-800/30 rounded-lg">
            <p className="text-red-400">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-300 hover:text-red-200"
            >
              Dismiss
            </button>
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

        {/* System Status */}
        <div className="mb-8">
          <SystemStatus />
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
