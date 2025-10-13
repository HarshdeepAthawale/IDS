'use client'

import { useState } from 'react'

export default function AlertTable({ alerts = [] }) {
  const [sortField, setSortField] = useState('timestamp')
  const [sortDirection, setSortDirection] = useState('desc')

  const getSeverityBadge = (severity) => {
    const severityClasses = {
      low: 'alert-low',
      medium: 'alert-medium',
      high: 'alert-high',
      critical: 'alert-critical'
    }
    
    return (
      <span className={`alert-badge ${severityClasses[severity] || severityClasses.low}`}>
        {severity?.toUpperCase() || 'UNKNOWN'}
      </span>
    )
  }

  const getTypeIcon = (type) => {
    const icons = {
      dos: '🚨',
      port_scan: '🔍',
      suspicious_volume: '📊',
      default: '⚠️'
    }
    return icons[type] || icons.default
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHour = Math.floor(diffMin / 60)

    if (diffSec < 60) {
      return `${diffSec}s ago`
    } else if (diffMin < 60) {
      return `${diffMin}m ago`
    } else if (diffHour < 24) {
      return `${diffHour}h ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  const formatFullTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const sortedAlerts = [...alerts].sort((a, b) => {
    let aVal = a[sortField]
    let bVal = b[sortField]

    // Handle timestamp sorting
    if (sortField === 'timestamp') {
      aVal = new Date(aVal).getTime()
      bVal = new Date(bVal).getTime()
    }

    // Handle severity sorting
    if (sortField === 'severity') {
      const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 }
      aVal = severityOrder[aVal] || 0
      bVal = severityOrder[bVal] || 0
    }

    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })

  if (alerts.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🛡️</div>
        <h3 className="text-lg font-semibold text-dark-text mb-2">No Alerts</h3>
        <p className="text-dark-text-muted">No security alerts detected at this time.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-dark-border">
            <th 
              className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted cursor-pointer hover:text-dark-text"
              onClick={() => handleSort('timestamp')}
            >
              <div className="flex items-center space-x-1">
                <span>Time</span>
                {sortField === 'timestamp' && (
                  <span className="text-xs">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </div>
            </th>
            <th 
              className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted cursor-pointer hover:text-dark-text"
              onClick={() => handleSort('type')}
            >
              <div className="flex items-center space-x-1">
                <span>Type</span>
                {sortField === 'type' && (
                  <span className="text-xs">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </div>
            </th>
            <th 
              className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted cursor-pointer hover:text-dark-text"
              onClick={() => handleSort('severity')}
            >
              <div className="flex items-center space-x-1">
                <span>Severity</span>
                {sortField === 'severity' && (
                  <span className="text-xs">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </div>
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">
              Source IP
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedAlerts.map((alert, index) => (
            <tr 
              key={alert.id || index}
              className="border-b border-dark-border hover:bg-dark-surface/50 transition-colors"
            >
              <td className="py-3 px-4">
                <div className="text-sm">
                  <div className="text-dark-text font-mono">
                    {formatTimestamp(alert.timestamp)}
                  </div>
                  <div className="text-xs text-dark-text-muted">
                    {formatFullTimestamp(alert.timestamp)}
                  </div>
                </div>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">{getTypeIcon(alert.type)}</span>
                  <span className="text-sm text-dark-text font-medium">
                    {alert.type?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
              </td>
              <td className="py-3 px-4">
                {getSeverityBadge(alert.severity)}
              </td>
              <td className="py-3 px-4">
                <span className="text-sm font-mono text-dark-text bg-dark-surface px-2 py-1 rounded">
                  {alert.source_ip || 'N/A'}
                </span>
              </td>
              <td className="py-3 px-4">
                <div className="text-sm text-dark-text max-w-xs">
                  <div className="truncate">
                    {alert.description || 'No description available'}
                  </div>
                  {alert.details && (
                    <div className="text-xs text-dark-text-muted mt-1">
                      {Object.entries(alert.details).slice(0, 2).map(([key, value]) => (
                        <span key={key} className="mr-3">
                          {key}: {typeof value === 'number' ? value.toFixed(2) : value}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
