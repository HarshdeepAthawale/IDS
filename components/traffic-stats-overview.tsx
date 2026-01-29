"use client"

import { useState, useEffect, useCallback, useMemo, memo, startTransition } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { flaskApi } from "@/lib/flask-api"
import { RefreshCw } from "lucide-react"
import { useWebSocket } from "@/hooks/use-websocket"
import { useDebounce } from "@/hooks/use-debounce"

interface ProtocolData {
  name: string
  value: number
  count?: number
}

// Protocol-specific color mapping
const PROTOCOL_COLORS: Record<string, string> = {
  'TCP': '#3b82f6',      // Blue
  'UDP': '#ef4444',      // Red
  'ICMP': '#10b981',     // Green
  'ICMPv6': '#22c55e',   // Light green
  'IPv6': '#8b5cf6',     // Purple
  'IPv4': '#6366f1',     // Indigo
  'ARP': '#f59e0b',      // Orange
  'GRE': '#ec4899',      // Pink
  'ESP': '#06b6d4',      // Cyan
  'AH': '#14b8a6',       // Teal
  'OSPF': '#a855f7',     // Violet
  'SCTP': '#f97316',     // Orange
  'IGMP': '#84cc16',     // Lime
  'HOPOPT': '#64748b',   // Slate
  'Other': '#6b7280',    // Gray
}

// Fallback colors for unknown protocols
const FALLBACK_COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]

/**
 * Normalize protocol name to consistent format
 */
function normalizeProtocolName(protocol: any): string {
  if (!protocol) return 'Other'
  
  if (typeof protocol === 'string') {
    const upper = protocol.toUpperCase().trim()
    // Handle common variations
    if (upper === 'ICMPV6') return 'ICMPv6'
    if (upper === 'IPV6') return 'IPv6'
    if (upper === 'IPV4') return 'IPv4'
    if (upper === 'UNKNOWN' || upper === '') return 'Other'
    return upper
  }
  
  if (typeof protocol === 'number') {
    // Map common protocol numbers
    const protocolMap: Record<number, string> = {
      1: 'ICMP',
      6: 'TCP',
      17: 'UDP',
      41: 'IPv6',
      47: 'GRE',
      50: 'ESP',
      51: 'AH',
      58: 'ICMPv6',
      89: 'OSPF',
      132: 'SCTP',
    }
    return protocolMap[protocol] || `Protocol-${protocol}`
  }
  
  try {
    const str = String(protocol).toUpperCase().trim()
    return str || 'Other'
  } catch {
    return 'Other'
  }
}

/**
 * Get color for a protocol
 */
function getProtocolColor(protocolName: string, index: number): string {
  const normalized = normalizeProtocolName(protocolName)
  return PROTOCOL_COLORS[normalized] || FALLBACK_COLORS[index % FALLBACK_COLORS.length]
}

function TrafficStatsOverview() {
  const [protocolData, setProtocolData] = useState<ProtocolData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Real-time WebSocket connection
  const { isConnected, on, off } = useWebSocket({ room: 'dashboard' })
  
  // Debounced state for rapid updates
  const [pendingProtocolUpdate, setPendingProtocolUpdate] = useState<ProtocolData[] | null>(null)
  const debouncedProtocolUpdate = useDebounce(pendingProtocolUpdate, 100)

  const fetchProtocolData = useCallback(async () => {
    try {
      setError(null)
      
      let protocolData: ProtocolData[] = []
      const targetProtocols = ['TCP', 'ARP', 'UDP']
      
      // Try protocol stats endpoint first
      try {
        const protocolResponse = await flaskApi.getProtocolStats({ hours: 24, limit: 10 })
        console.log('[TrafficStatsOverview] Protocol stats response:', protocolResponse)
        
        if (protocolResponse?.protocol_distribution) {
          protocolData = Object.entries(protocolResponse.protocol_distribution)
            .map(([name, value]: [string, any]) => {
              // Normalize protocol name
              const normalizedName = normalizeProtocolName(name)
              
              // Handle both number and object formats
              let numericValue = 0
              let packetCount = 0
              
              if (typeof value === 'number') {
                numericValue = value
                packetCount = value
              } else if (typeof value === 'object' && value !== null) {
                numericValue = value.percentage || 0
                packetCount = value.total_packets || 0
              }
              
              return { 
                name: normalizedName, 
                value: numericValue,
                count: packetCount
              };
            })
            .filter(item => {
              // Only include TCP, ARP, UDP with valid data
              return item.value > 0 && targetProtocols.includes(item.name)
            })
            .sort((a, b) => {
              // Sort: TCP first, then ARP, then UDP
              const order = { 'TCP': 0, 'ARP': 1, 'UDP': 2 }
              return (order[a.name as keyof typeof order] ?? 99) - (order[b.name as keyof typeof order] ?? 99)
            })
        }
      } catch (protocolErr) {
        console.warn('[TrafficStatsOverview] Protocol stats endpoint failed, trying traffic stats:', protocolErr)
        
        // Fallback: try to get protocol data from traffic stats endpoint
        try {
          const trafficResponse = await flaskApi.getTrafficStats({ hours: 24, limit: 24 })
          console.log('[TrafficStatsOverview] Traffic stats response:', trafficResponse)
          
          if (trafficResponse?.current_stats?.protocol_distribution) {
            const protocolDist = trafficResponse.current_stats.protocol_distribution
            const entries = Object.entries(protocolDist)
            const total = entries.reduce((sum, [, val]) => {
              return sum + (typeof val === 'number' ? val : 0)
            }, 0)
            
            protocolData = entries
              .map(([name, value]: [string, any]) => {
                const normalizedName = normalizeProtocolName(name)
                const count = typeof value === 'number' ? value : 0
                const percentage = total > 0 ? Math.round((count / total) * 100 * 100) / 100 : 0
                return { 
                  name: normalizedName, 
                  value: percentage,
                  count: count
                }
              })
              .filter(item => {
                // Only include TCP, ARP, UDP with valid data
                return item.value > 0 && targetProtocols.includes(item.name)
              })
              .sort((a, b) => {
                // Sort: TCP first, then ARP, then UDP
                const order = { 'TCP': 0, 'ARP': 1, 'UDP': 2 }
                return (order[a.name as keyof typeof order] ?? 99) - (order[b.name as keyof typeof order] ?? 99)
              })
          }
        } catch (trafficErr) {
          console.error('[TrafficStatsOverview] Traffic stats fallback also failed:', trafficErr)
        }
      }
      
      if (protocolData.length > 0) {
        setProtocolData(protocolData)
        console.log('[TrafficStatsOverview] Fetched protocol data:', protocolData)
      } else {
        console.warn('[TrafficStatsOverview] No protocol data found after API fetch. Details:', {
          protocolDataLength: protocolData.length,
          willWaitForWebSocket: true
        })
        // Don't clear existing data - keep what we have from WebSocket
      }
    } catch (err) {
      console.error('Error fetching protocol stats:', err)
      setError('Failed to fetch protocol data')
      // Don't clear existing data on error - keep what we have from WebSocket
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchProtocolData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  // Periodic refresh every 30 seconds
  useEffect(() => {
    const refreshInterval = setInterval(() => {
      console.log('[TrafficStatsOverview] Periodic refresh (30s) - fetching protocol data...')
      fetchProtocolData()
    }, 30000) // 30 seconds

    return () => clearInterval(refreshInterval)
  }, [fetchProtocolData])

  // Apply debounced protocol updates (optimized to prevent unnecessary re-renders)
  useEffect(() => {
    if (debouncedProtocolUpdate) {
      startTransition(() => {
        setProtocolData(prev => {
          // Only update if data actually changed
          const prevStr = JSON.stringify(prev)
          const newStr = JSON.stringify(debouncedProtocolUpdate)
          if (prevStr === newStr) {
            return prev // No change, return same reference
          }
          return debouncedProtocolUpdate
        })
      })
      setPendingProtocolUpdate(null)
    }
  }, [debouncedProtocolUpdate])

  // Real-time WebSocket updates (with debouncing)
  useEffect(() => {
    console.log('[TrafficStatsOverview] WebSocket connection status:', isConnected)
    
    if (!isConnected) {
      console.log('[TrafficStatsOverview] WebSocket not connected, using polling fallback')
      // Only use polling as true fallback when WebSocket is disconnected
      const fallbackInterval = setInterval(() => {
        console.log('[TrafficStatsOverview] Polling for protocol data...')
        fetchProtocolData()
      }, 5000)
      return () => clearInterval(fallbackInterval)
    }
    
    console.log('[TrafficStatsOverview] WebSocket connected, setting up listeners')

    const handleTrafficUpdate = (data: any) => {
      const trafficUpdate = data.data || data
      
      // Debug logging
      console.log('[TrafficStatsOverview] WebSocket update received:', trafficUpdate)
      
      // Queue protocol distribution update (will be debounced)
      if (trafficUpdate.protocol_distribution && Object.keys(trafficUpdate.protocol_distribution).length > 0) {
        // Target protocols: TCP, ARP, UDP
        const targetProtocols = ['TCP', 'ARP', 'UDP']
        
        // Filter to only TCP, ARP, UDP entries
        const protocolEntries = Object.entries(trafficUpdate.protocol_distribution)
          .filter(([name]) => {
            const normalizedName = normalizeProtocolName(name)
            return targetProtocols.includes(normalizedName)
          })
        
        if (protocolEntries.length === 0) {
          console.warn('[TrafficStatsOverview] No TCP/ARP/UDP protocols in WebSocket update')
          return
        }
        
        // WebSocket sends counts, not percentages - calculate total for filtered protocols only
        const total = protocolEntries.reduce((sum, [, value]) => {
          if (typeof value === 'number') {
            return sum + value
          } else if (typeof value === 'object' && value !== null && 'total_packets' in value) {
            return sum + (Number((value as { total_packets?: number }).total_packets) || 0)
          }
          return sum
        }, 0)
        
        // Convert counts to percentages for TCP, ARP, UDP only
        const protocolData = protocolEntries
          .map(([name, value]) => {
            const normalizedName = normalizeProtocolName(name)
            let numericValue = 0
            let packetCount = 0
            
            if (typeof value === 'number') {
              // WebSocket sends counts - convert to percentage
              packetCount = value
              numericValue = total > 0 ? Math.round((value / total) * 100 * 100) / 100 : 0
            } else if (typeof value === 'object' && value !== null) {
              // API format: object with percentage field
              const obj = value as { total_packets?: number; percentage?: number }
              packetCount = obj.total_packets ?? 0
              if ('percentage' in obj && obj.percentage != null) {
                numericValue = obj.percentage
              } else if (obj.total_packets != null && total > 0) {
                numericValue = Math.round((obj.total_packets / total) * 100 * 100) / 100
              }
            }
            
            return { 
              name: normalizedName, 
              value: numericValue,
              count: packetCount
            }
          })
          .filter(item => item.value > 0) // Only include protocols with data
          .sort((a, b) => {
            // Sort: TCP first, then ARP, then UDP
            const order = { 'TCP': 0, 'ARP': 1, 'UDP': 2 }
            return (order[a.name as keyof typeof order] ?? 99) - (order[b.name as keyof typeof order] ?? 99)
          })
        
        if (protocolData.length > 0) {
          console.log('[TrafficStatsOverview] Updating protocol data from WebSocket:', protocolData)
          setPendingProtocolUpdate(protocolData)
          setError(null) // Clear any errors when we get valid data
        } else {
          console.warn('[TrafficStatsOverview] Protocol data is empty after processing:', {
            protocolEntries,
            total,
            trafficUpdate: trafficUpdate.protocol_distribution
          })
        }
      } else {
        console.warn('[TrafficStatsOverview] No protocol_distribution in WebSocket update:', {
          hasProtocolDist: !!trafficUpdate.protocol_distribution,
          keys: Object.keys(trafficUpdate),
          trafficUpdate
        })
      }
    }

    on('traffic_update', handleTrafficUpdate)
    on('stats_update', handleTrafficUpdate)

    return () => {
      off('traffic_update', handleTrafficUpdate)
      off('stats_update', handleTrafficUpdate)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]) // on/off are stable from context

  // Validate and normalize pie data - filter to only TCP, ARP, UDP
  const pieData = useMemo(() => {
    if (!protocolData || protocolData.length === 0) {
      return []
    }
    
    // Target protocols: TCP, ARP, UDP
    const targetProtocols = ['TCP', 'ARP', 'UDP']
    
    // Filter to only TCP, ARP, UDP with valid data
    const validData = protocolData
      .filter(item => {
        // Validate item structure
        if (!item || typeof item.name !== 'string' || typeof item.value !== 'number') {
          return false
        }
        
        const normalizedName = normalizeProtocolName(item.name)
        // Only include TCP, ARP, UDP
        if (!targetProtocols.includes(normalizedName)) {
          return false
        }
        
        // Only include protocols with valid positive values
        if (item.value <= 0 || isNaN(item.value) || !isFinite(item.value)) {
          return false
        }
        return true
      })
      .map(item => ({
        name: normalizeProtocolName(item.name),
        value: Math.max(0, Math.min(100, item.value)), // Clamp between 0-100
        count: item.count || 0
      }))
      .sort((a, b) => {
        // Sort: TCP first, then ARP, then UDP
        const order = { 'TCP': 0, 'ARP': 1, 'UDP': 2 }
        return (order[a.name as keyof typeof order] ?? 99) - (order[b.name as keyof typeof order] ?? 99)
      })
    
    // If no valid data, return empty array
    if (validData.length === 0) {
      return []
    }
    
    // Recalculate percentages to sum to 100% if needed
    const totalPercentage = validData.reduce((sum, item) => sum + item.value, 0)
    if (totalPercentage > 0 && Math.abs(totalPercentage - 100) > 0.1) {
      // Normalize percentages to sum to 100%
      validData.forEach(item => {
        item.value = Math.round((item.value / totalPercentage) * 100 * 10) / 10
      })
    }
    
    console.log('[TrafficStatsOverview] pieData computed (TCP/ARP/UDP only):', validData)
    return validData
  }, [protocolData])

  return (
    <div className="grid grid-cols-1 gap-6">
      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            Protocol Distribution
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardTitle>
          <button
            onClick={() => {
              setLoading(true)
              fetchProtocolData()
            }}
            className="p-1 hover:bg-muted rounded"
            title="Refresh protocol data"
          >
            <RefreshCw className="h-4 w-4 text-muted-foreground hover:text-foreground" />
          </button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              Loading protocol data...
            </div>
          ) : pieData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground gap-2">
              <p>No protocol data available</p>
              {error && (
                <p className="text-xs text-destructive/80">
                  {error}
                </p>
              )}
              <p className="text-xs">
                {isConnected ? 'Waiting for real-time updates...' : 'Connect to backend to see protocol distribution'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(props: Record<string, unknown>) => {
                        const name = String(props.name ?? '')
                        const num = Number(props.value ?? 0)
                        if (num > 0) {
                          return `${name}\n${num.toFixed(1)}%`
                        }
                        return ''
                      }}
                      outerRadius={100}
                      innerRadius={30}
                      fill="#8884d8"
                      dataKey="value"
                      isAnimationActive={true}
                      animationDuration={500}
                      animationEasing="ease-out"
                    >
                      {pieData.map((entry, index) => (
                        <Cell 
                          key={`cell-${entry.name}-${index}`} 
                          fill={getProtocolColor(entry.name, index)} 
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--popover))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "6px",
                        padding: "8px 12px"
                      }}
                      labelStyle={{ 
                        color: "hsl(var(--foreground))",
                        fontWeight: 600,
                        marginBottom: "4px"
                      }}
                      itemStyle={{ color: "hsl(var(--foreground))" }}
                      animationDuration={200}
                      formatter={(value: any, name: string, props: any) => {
                        const payload = props.payload
                        const count = payload?.count || 0
                        return [
                          `${value.toFixed(1)}%${count > 0 ? ` (${count.toLocaleString()} packets)` : ''}`,
                          'Percentage'
                        ]
                      }}
                      labelFormatter={(label: string) => `Protocol: ${label}`}
                    />
                </PieChart>
              </ResponsiveContainer>
              
              {/* Protocol Legend - Only TCP, ARP, UDP */}
              {pieData.length > 0 && (
                <div className="flex items-center justify-center gap-6 mt-4">
                  {pieData.map((entry, index) => (
                    <div 
                      key={`legend-${entry.name}-${index}`}
                      className="flex items-center gap-2 text-sm"
                    >
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: getProtocolColor(entry.name, index) }}
                      />
                      <span className="text-foreground font-medium">{entry.name}</span>
                      <span className="text-muted-foreground">
                        {entry.value.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default memo(TrafficStatsOverview)
