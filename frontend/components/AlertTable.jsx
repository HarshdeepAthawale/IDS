'use client'

import { useState, useMemo } from 'react'

export default function AlertTable({ alerts = [], onFilterChange, currentFilters = {} }) {
  const [sortField, setSortField] = useState('timestamp')
  const [sortDirection, setSortDirection] = useState('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(25)

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

  // Filter alerts based on current filters
  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      // Severity filter
      if (currentFilters.severity && alert.severity !== currentFilters.severity) {
        return false
      }
      
      // Type filter
      if (currentFilters.type && alert.type !== currentFilters.type) {
        return false
      }
      
      // Source IP filter
      if (currentFilters.source_ip && !alert.source_ip?.includes(currentFilters.source_ip)) {
        return false
      }
      
      // Time range filter
      if (currentFilters.timeRange && currentFilters.timeRange !== 'all') {
        const alertTime = new Date(alert.timestamp).getTime()
        const now = Date.now()
        const timeRanges = {
          '1h': 60 * 60 * 1000,
          '24h': 24 * 60 * 60 * 1000,
          '7d': 7 * 24 * 60 * 60 * 1000
        }
        
        if (now - alertTime > timeRanges[currentFilters.timeRange]) {
          return false
        }
      }
      
      return true
    })
  }, [alerts, currentFilters])

  // Sort filtered alerts
  const sortedAlerts = useMemo(() => {
    return [...filteredAlerts].sort((a, b) => {
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
  }, [filteredAlerts, sortField, sortDirection])

  // Paginate sorted alerts
  const paginatedAlerts = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    const endIndex = startIndex + itemsPerPage
    return sortedAlerts.slice(startIndex, endIndex)
  }, [sortedAlerts, currentPage, itemsPerPage])

  const totalPages = Math.ceil(sortedAlerts.length / itemsPerPage)

  const handlePageChange = (page) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (newItemsPerPage) => {
    setItemsPerPage(newItemsPerPage)
    setCurrentPage(1) // Reset to first page
  }

  if (alerts.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🛡️</div>
        <h3 className="text-lg font-semibold text-dark-text mb-2">No Alerts</h3>
        <p className="text-dark-text-muted">No security alerts detected at this time.</p>
      </div>
    )
  }

  if (filteredAlerts.length === 0 && alerts.length > 0) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">🔍</div>
        <h3 className="text-lg font-semibold text-dark-text mb-2">No Matching Alerts</h3>
        <p className="text-dark-text-muted">No alerts match the current filters.</p>
        <button
          onClick={() => onFilterChange && onFilterChange({})}
          className="mt-4 text-sm text-dark-accent hover:text-dark-accent-hover"
        >
          Clear Filters
        </button>
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
          {paginatedAlerts.map((alert, index) => (
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

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-dark-border">
          <div className="flex items-center space-x-4">
            <div className="text-sm text-dark-text-muted">
              Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, sortedAlerts.length)} of {sortedAlerts.length} alerts
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-sm text-dark-text-muted">Per page:</label>
              <select
                value={itemsPerPage}
                onChange={(e) => handleItemsPerPageChange(parseInt(e.target.value))}
                className="bg-dark-card border border-dark-border rounded px-2 py-1 text-sm text-dark-text"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm bg-dark-surface border border-dark-border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-dark-border transition-colors"
            >
              Previous
            </button>
            
            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (currentPage <= 3) {
                  pageNum = i + 1
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = currentPage - 2 + i
                }
                
                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`px-3 py-1 text-sm rounded transition-colors ${
                      currentPage === pageNum
                        ? 'bg-dark-accent text-white'
                        : 'bg-dark-surface border border-dark-border hover:bg-dark-border text-dark-text'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm bg-dark-surface border border-dark-border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-dark-border transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
