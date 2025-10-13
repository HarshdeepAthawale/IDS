'use client'

import { useState, useEffect } from 'react'
import { apiService } from '../lib/api'

export default function SystemStatus() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [packetStatus, setPacketStatus] = useState(null)
  const [idsStatus, setIdsStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadSystemStatus()
    const interval = setInterval(loadSystemStatus, 10000) // Update every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const loadSystemStatus = async () => {
    try {
      setError(null)
      const [systemData, packetData, idsData] = await Promise.all([
        apiService.getSystemInfo(),
        apiService.getPacketStatus(),
        apiService.getIDSStatus()
      ])
      
      setSystemInfo(systemData)
      setPacketStatus(packetData)
      setIdsStatus(idsData)
      setLoading(false)
    } catch (err) {
      console.error('Error loading system status:', err)
      setError(err.message)
      setLoading(false)
    }
  }

  const getStatusBadge = (status, isRunning) => {
    if (loading) {
      return <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">Loading...</span>
    }
    
    if (error) {
      return <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">Error</span>
    }
    
    if (isRunning) {
      return <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">Running</span>
    }
    
    return <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">Stopped</span>
  }

  const formatUptime = (seconds) => {
    if (!seconds) return 'Unknown'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    }
    return `${secs}s`
  }

  if (loading && !systemInfo) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4 text-dark-text">System Status</h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-dark-accent"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-dark-text">System Status</h2>
        <button
          onClick={loadSystemStatus}
          className="p-1 hover:bg-dark-border rounded transition-colors"
          title="Refresh Status"
        >
          <svg className="w-4 h-4 text-dark-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-800/30 rounded-lg">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Packet Capture Status */}
        <div className="bg-dark-surface rounded-lg p-4 border border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-dark-text">Packet Capture</h3>
            {getStatusBadge('packet', packetStatus?.isCapturing)}
          </div>
          <div className="space-y-1 text-xs text-dark-text-muted">
            <div>Interface: {packetStatus?.interface || 'None'}</div>
            <div>Buffer: {packetStatus?.bufferSize || 0} packets</div>
            <div>Available: {packetStatus?.totalInterfaces || 0} interfaces</div>
          </div>
        </div>

        {/* IDS Engine Status */}
        <div className="bg-dark-surface rounded-lg p-4 border border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-dark-text">IDS Engine</h3>
            {getStatusBadge('ids', idsStatus?.isRunning)}
          </div>
          <div className="space-y-1 text-xs text-dark-text-muted">
            <div>Analysis: {idsStatus?.analysisInterval || 0}ms</div>
            <div>Tracking: {idsStatus?.trackingStats?.ipPacketCounts || 0} IPs</div>
            <div>Alerts: {idsStatus?.trackingStats?.recentAlerts || 0} recent</div>
          </div>
        </div>

        {/* System Information */}
        <div className="bg-dark-surface rounded-lg p-4 border border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-dark-text">System</h3>
            {getStatusBadge('system', systemInfo?.status === 'OK')}
          </div>
          <div className="space-y-1 text-xs text-dark-text-muted">
            <div>Uptime: {formatUptime(systemInfo?.uptime)}</div>
            <div>Status: {systemInfo?.status || 'Unknown'}</div>
            <div>Last Update: {systemInfo?.timestamp ? new Date(systemInfo.timestamp).toLocaleTimeString() : 'Unknown'}</div>
          </div>
        </div>
      </div>

      {/* IDS Configuration */}
      {idsStatus?.config && (
        <div className="mt-6 pt-4 border-t border-dark-border">
          <h3 className="text-sm font-medium text-dark-text mb-3">Detection Thresholds</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-dark-surface rounded p-3">
              <div className="text-dark-text-muted mb-1">DoS Detection</div>
              <div className="text-dark-text">
                {idsStatus.config.dos?.threshold || 0} packets/sec
              </div>
              <div className="text-dark-text-muted">
                in {idsStatus.config.dos?.timeWindow || 0}ms
              </div>
            </div>
            <div className="bg-dark-surface rounded p-3">
              <div className="text-dark-text-muted mb-1">Port Scan Detection</div>
              <div className="text-dark-text">
                {idsStatus.config.port_scan?.threshold || 0} ports
              </div>
              <div className="text-dark-text-muted">
                in {idsStatus.config.port_scan?.timeWindow || 0}ms
              </div>
            </div>
            <div className="bg-dark-surface rounded p-3">
              <div className="text-dark-text-muted mb-1">Suspicious Volume</div>
              <div className="text-dark-text">
                {idsStatus.config.suspicious_volume?.threshold || 0} MB
              </div>
              <div className="text-dark-text-muted">
                in {idsStatus.config.suspicious_volume?.timeWindow || 0}ms
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
