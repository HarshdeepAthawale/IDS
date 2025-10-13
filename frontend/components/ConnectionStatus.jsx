'use client'

import { useState, useEffect } from 'react'
import { socketService } from '../lib/socket'
import { connectionManager } from '../lib/connectionManager'

export default function ConnectionStatus() {
  const [connectionState, setConnectionState] = useState('disconnected')
  const [connectionInfo, setConnectionInfo] = useState(null)
  const [networkStatus, setNetworkStatus] = useState('online')
  const [healthStatus, setHealthStatus] = useState('unknown')

  useEffect(() => {
    // Socket connection state listeners
    socketService.on('connection-state', (data) => {
      setConnectionState(data.state)
      setConnectionInfo(socketService.getConnectionInfo())
    })

    // Network status listeners
    connectionManager.on('network', (data) => {
      setNetworkStatus(data.status)
    })

    // Health check listeners
    connectionManager.on('health', (data) => {
      setHealthStatus(data.status)
    })

    // Initial state
    setConnectionInfo(socketService.getConnectionInfo())
    setNetworkStatus(navigator.onLine ? 'online' : 'offline')

    // Start health checks
    connectionManager.startHealthChecks()

    return () => {
      connectionManager.stopHealthChecks()
    }
  }, [])

  const getStatusColor = () => {
    if (networkStatus === 'offline') return 'text-red-400'
    if (connectionState === 'connected' && healthStatus === 'healthy') return 'text-green-400'
    if (connectionState === 'connecting') return 'text-yellow-400'
    if (connectionState === 'error') return 'text-red-400'
    return 'text-gray-400'
  }

  const getStatusText = () => {
    if (networkStatus === 'offline') return 'Network Offline'
    if (connectionState === 'connected' && healthStatus === 'healthy') return 'Connected & Healthy'
    if (connectionState === 'connected' && healthStatus === 'unhealthy') return 'Connected (Unhealthy)'
    if (connectionState === 'connecting') return 'Connecting...'
    if (connectionState === 'error') return 'Connection Error'
    return 'Disconnected'
  }

  const getUptime = () => {
    if (connectionInfo?.uptime) {
      const seconds = Math.floor(connectionInfo.uptime / 1000)
      const minutes = Math.floor(seconds / 60)
      const hours = Math.floor(minutes / 60)
      
      if (hours > 0) {
        return `${hours}h ${minutes % 60}m`
      } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`
      }
      return `${seconds}s`
    }
    return null
  }

  const handleReconnect = () => {
    socketService.reconnect()
  }

  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-dark-text">Connection Status</h3>
        <button
          onClick={handleReconnect}
          className="text-xs text-dark-accent hover:text-dark-accent-hover transition-colors"
          title="Reconnect"
        >
          Reconnect
        </button>
      </div>

      <div className="space-y-3">
        {/* Main Status */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-dark-text-muted">Status</span>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              networkStatus === 'offline' ? 'bg-red-500' :
              connectionState === 'connected' && healthStatus === 'healthy' ? 'bg-green-500 animate-pulse-slow' :
              connectionState === 'connecting' ? 'bg-yellow-500 animate-bounce-slow' :
              'bg-red-500'
            }`} />
            <span className={`text-xs font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </span>
          </div>
        </div>

        {/* Network Status */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-dark-text-muted">Network</span>
          <span className={`text-xs font-medium ${
            networkStatus === 'online' ? 'text-green-400' : 'text-red-400'
          }`}>
            {networkStatus === 'online' ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* WebSocket Status */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-dark-text-muted">WebSocket</span>
          <span className={`text-xs font-medium ${
            connectionState === 'connected' ? 'text-green-400' : 'text-red-400'
          }`}>
            {connectionState}
          </span>
        </div>

        {/* Backend Health */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-dark-text-muted">Backend</span>
          <span className={`text-xs font-medium ${
            healthStatus === 'healthy' ? 'text-green-400' : 'text-red-400'
          }`}>
            {healthStatus}
          </span>
        </div>

        {/* Connection Uptime */}
        {connectionInfo?.uptime && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-dark-text-muted">Uptime</span>
            <span className="text-xs font-mono text-dark-text">
              {getUptime()}
            </span>
          </div>
        )}

        {/* Reconnection Attempts */}
        {connectionInfo?.reconnectAttempts > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-dark-text-muted">Reconnects</span>
            <span className="text-xs text-yellow-400">
              {connectionInfo.reconnectAttempts}/{connectionInfo.maxReconnectAttempts}
            </span>
          </div>
        )}
      </div>

      {/* Connection Details */}
      {connectionInfo?.lastConnectedAt && (
        <div className="mt-3 pt-3 border-t border-dark-border">
          <div className="text-xs text-dark-text-muted">
            Last connected: {new Date(connectionInfo.lastConnectedAt).toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  )
}
