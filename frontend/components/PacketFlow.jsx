'use client'

import { useState, useEffect } from 'react'

export default function PacketFlow({ packets = [] }) {
  const [flowData, setFlowData] = useState([])

  useEffect(() => {
    // Process packets to create flow visualization data
    const processedFlows = processPacketFlows(packets)
    setFlowData(processedFlows)
  }, [packets])

  const processPacketFlows = (packets) => {
    // Group packets by source-destination pairs
    const flows = new Map()
    
    packets.slice(-50).forEach(packet => { // Last 50 packets for performance
      const key = `${packet.src_ip}-${packet.dst_ip}`
      if (!flows.has(key)) {
        flows.set(key, {
          src_ip: packet.src_ip,
          dst_ip: packet.dst_ip,
          protocol: packet.protocol,
          packet_count: 0,
          total_bytes: 0,
          last_seen: packet.timestamp,
          ports: new Set()
        })
      }
      
      const flow = flows.get(key)
      flow.packet_count++
      flow.total_bytes += packet.size || 0
      flow.last_seen = Math.max(flow.last_seen, packet.timestamp)
      
      if (packet.dst_port) {
        flow.ports.add(packet.dst_port)
      }
    })

    return Array.from(flows.values())
      .sort((a, b) => b.packet_count - a.packet_count)
      .slice(0, 10) // Top 10 flows
  }

  const formatBytes = (bytes) => {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    } else if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${bytes} B`
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffSec = Math.floor(diffMs / 1000)

    if (diffSec < 60) {
      return `${diffSec}s ago`
    } else if (diffSec < 3600) {
      return `${Math.floor(diffSec / 60)}m ago`
    }
    return date.toLocaleTimeString()
  }

  const getProtocolColor = (protocol) => {
    const colors = {
      TCP: 'text-blue-400',
      UDP: 'text-green-400',
      ICMP: 'text-yellow-400',
      default: 'text-gray-400'
    }
    return colors[protocol] || colors.default
  }

  if (flowData.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="text-4xl mb-2">🌐</div>
        <p className="text-dark-text-muted">No packet flows detected</p>
        <p className="text-sm text-dark-text-muted mt-1">
          Network flows will appear here as packets are captured
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="text-sm text-dark-text-muted mb-4">
        Top {flowData.length} active flows
      </div>
      
      {flowData.map((flow, index) => (
        <div key={`${flow.src_ip}-${flow.dst_ip}`} className="bg-dark-surface rounded-lg p-4 border border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-dark-text-muted bg-dark-card px-2 py-1 rounded">
                #{index + 1}
              </span>
              <span className={`text-sm font-medium ${getProtocolColor(flow.protocol)}`}>
                {flow.protocol}
              </span>
            </div>
            <span className="text-xs text-dark-text-muted">
              {formatTimestamp(flow.last_seen)}
            </span>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <div className="text-xs text-dark-text-muted mb-1">Source</div>
              <div className="font-mono text-sm text-dark-text">{flow.src_ip}</div>
            </div>
            <div>
              <div className="text-xs text-dark-text-muted mb-1">Destination</div>
              <div className="font-mono text-sm text-dark-text">{flow.dst_ip}</div>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 text-xs">
              <div className="flex items-center space-x-1">
                <span className="text-dark-text-muted">Packets:</span>
                <span className="text-dark-text font-semibold">{flow.packet_count}</span>
              </div>
              <div className="flex items-center space-x-1">
                <span className="text-dark-text-muted">Size:</span>
                <span className="text-dark-text font-semibold">{formatBytes(flow.total_bytes)}</span>
              </div>
              {flow.ports.size > 0 && (
                <div className="flex items-center space-x-1">
                  <span className="text-dark-text-muted">Ports:</span>
                  <span className="text-dark-text font-semibold">{flow.ports.size}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${
                flow.packet_count > 100 ? 'bg-red-500' : 
                flow.packet_count > 50 ? 'bg-yellow-500' : 'bg-green-500'
              }`} />
              <span className="text-xs text-dark-text-muted">
                {flow.packet_count > 100 ? 'High' : flow.packet_count > 50 ? 'Medium' : 'Low'}
              </span>
            </div>
          </div>
          
          {flow.ports.size > 0 && (
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className="text-xs text-dark-text-muted mb-1">Ports:</div>
              <div className="flex flex-wrap gap-1">
                {Array.from(flow.ports).slice(0, 8).map(port => (
                  <span key={port} className="text-xs bg-dark-card px-2 py-1 rounded font-mono text-dark-text">
                    {port}
                  </span>
                ))}
                {flow.ports.size > 8 && (
                  <span className="text-xs text-dark-text-muted">+{flow.ports.size - 8} more</span>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
