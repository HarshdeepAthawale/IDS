'use client'

import { useState } from 'react'

export default function AlertFilters({ onFilterChange, currentFilters = {} }) {
  const [filters, setFilters] = useState({
    severity: currentFilters.severity || '',
    type: currentFilters.type || '',
    source_ip: currentFilters.source_ip || '',
    timeRange: currentFilters.timeRange || 'all'
  })

  const severityOptions = [
    { value: '', label: 'All Severities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' }
  ]

  const typeOptions = [
    { value: '', label: 'All Types' },
    { value: 'dos', label: 'DoS Attack' },
    { value: 'port_scan', label: 'Port Scan' },
    { value: 'suspicious_volume', label: 'Suspicious Volume' }
  ]

  const timeRangeOptions = [
    { value: 'all', label: 'All Time' },
    { value: '1h', label: 'Last Hour' },
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' }
  ]

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const clearFilters = () => {
    const clearedFilters = {
      severity: '',
      type: '',
      source_ip: '',
      timeRange: 'all'
    }
    setFilters(clearedFilters)
    onFilterChange(clearedFilters)
  }

  const hasActiveFilters = Object.values(filters).some(value => value !== '' && value !== 'all')

  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-dark-text">Filter Alerts</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-xs text-dark-text-muted hover:text-dark-text transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Severity Filter */}
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Severity</label>
          <select
            value={filters.severity}
            onChange={(e) => handleFilterChange('severity', e.target.value)}
            className="w-full bg-dark-card border border-dark-border rounded px-3 py-2 text-sm text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent"
          >
            {severityOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Type Filter */}
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Alert Type</label>
          <select
            value={filters.type}
            onChange={(e) => handleFilterChange('type', e.target.value)}
            className="w-full bg-dark-card border border-dark-border rounded px-3 py-2 text-sm text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent"
          >
            {typeOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Source IP Filter */}
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Source IP</label>
          <input
            type="text"
            value={filters.source_ip}
            onChange={(e) => handleFilterChange('source_ip', e.target.value)}
            placeholder="e.g., 192.168.1.1"
            className="w-full bg-dark-card border border-dark-border rounded px-3 py-2 text-sm text-dark-text placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-dark-accent"
          />
        </div>

        {/* Time Range Filter */}
        <div>
          <label className="block text-xs text-dark-text-muted mb-1">Time Range</label>
          <select
            value={filters.timeRange}
            onChange={(e) => handleFilterChange('timeRange', e.target.value)}
            className="w-full bg-dark-card border border-dark-border rounded px-3 py-2 text-sm text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent"
          >
            {timeRangeOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="mt-4 pt-4 border-t border-dark-border">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-dark-text-muted">Active filters:</span>
            {filters.severity && (
              <span className="inline-flex items-center px-2 py-1 bg-dark-accent/20 text-dark-accent text-xs rounded">
                Severity: {severityOptions.find(o => o.value === filters.severity)?.label}
                <button
                  onClick={() => handleFilterChange('severity', '')}
                  className="ml-1 hover:text-dark-accent-hover"
                >
                  ×
                </button>
              </span>
            )}
            {filters.type && (
              <span className="inline-flex items-center px-2 py-1 bg-dark-accent/20 text-dark-accent text-xs rounded">
                Type: {typeOptions.find(o => o.value === filters.type)?.label}
                <button
                  onClick={() => handleFilterChange('type', '')}
                  className="ml-1 hover:text-dark-accent-hover"
                >
                  ×
                </button>
              </span>
            )}
            {filters.source_ip && (
              <span className="inline-flex items-center px-2 py-1 bg-dark-accent/20 text-dark-accent text-xs rounded">
                IP: {filters.source_ip}
                <button
                  onClick={() => handleFilterChange('source_ip', '')}
                  className="ml-1 hover:text-dark-accent-hover"
                >
                  ×
                </button>
              </span>
            )}
            {filters.timeRange !== 'all' && (
              <span className="inline-flex items-center px-2 py-1 bg-dark-accent/20 text-dark-accent text-xs rounded">
                Time: {timeRangeOptions.find(o => o.value === filters.timeRange)?.label}
                <button
                  onClick={() => handleFilterChange('timeRange', 'all')}
                  className="ml-1 hover:text-dark-accent-hover"
                >
                  ×
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
