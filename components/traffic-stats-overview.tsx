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
      
      // Fetch protocol stats
      const protocolResponse = await flaskApi.getProtocolStats({ hours: 24, limit: 10 })
      
      // Extract protocol data from the dedicated protocol stats endpoint
      let protocolData: ProtocolData[] = []
      
      if (protocolResponse?.protocol_distribution) {
        protocolData = Object.entries(protocolResponse.protocol_distribution).map(([name, value]: [string, any]) => {
          // Handle both number and object formats
          const numericValue = typeof value === 'number' 
            ? value 
            : (typeof value === 'object' && value !== null && 'percentage' in value)
              ? value.percentage
              : 0;
          return { name, value: numericValue };
        })
      }
      
      setProtocolData(protocolData)
      console.log('[TrafficStatsOverview] Fetched protocol data:', protocolData)
    } catch (err) {
      console.error('Error fetching protocol stats:', err)
      setError('Failed to fetch protocol data')
      setProtocolData([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchProtocolData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

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
      if (trafficUpdate.protocol_distribution) {
        const protocolData = Object.entries(trafficUpdate.protocol_distribution).map(([name, value]) => {
          // Handle both number and object formats
          const numericValue = typeof value === 'number' 
            ? value 
            : (typeof value === 'object' && value !== null && 'percentage' in value)
              ? value.percentage
              : 0;
          return { name, value: numericValue };
        })
        setPendingProtocolUpdate(protocolData)
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

  const COLORS = useMemo(() => ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"], [])

  const pieData = useMemo(() => {
    // Create a stable reference - only change when data actually changes
    return protocolData.length > 0 ? protocolData : []
  }, [protocolData])

  return (
    <div className="grid grid-cols-1 gap-6">
      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            Protocol Distribution
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              Loading protocol data...
            </div>
          ) : pieData.length === 0 ? (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              No protocol data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name} ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  isAnimationActive={true}
                  animationDuration={400}
                  animationEasing="ease-out"
                  activeIndex={undefined}
                  activeShape={{ 
                    outerRadius: 90, 
                    fill: "#3b82f6",
                    stroke: "#fff",
                    strokeWidth: 2
                  }}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                  labelStyle={{ color: "#f3f4f6" }}
                  animationDuration={200}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default memo(TrafficStatsOverview)
