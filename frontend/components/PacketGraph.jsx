'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function PacketGraph({ data = [] }) {
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-dark-card border border-dark-border rounded-lg p-3 shadow-lg">
          <p className="text-sm text-dark-text-muted mb-1">{label}</p>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-dark-text">
                Packets: <span className="font-semibold">{data.packets}</span> pkt/s
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-sm text-dark-text">
                Traffic: <span className="font-semibold">{data.traffic}</span> MB/s
              </span>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  // If no data, show empty state
  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-center">
        <div>
          <div className="text-4xl mb-2">📊</div>
          <p className="text-dark-text-muted">No packet data available</p>
          <p className="text-sm text-dark-text-muted mt-1">
            Data will appear here once packets are being captured
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis 
            dataKey="time" 
            stroke="#9CA3AF"
            fontSize={12}
            tick={{ fill: '#9CA3AF' }}
            tickFormatter={(value) => {
              // Show only every 5th label to avoid crowding
              const index = data.findIndex(item => item.time === value)
              return index % 5 === 0 ? value : ''
            }}
          />
          <YAxis 
            stroke="#9CA3AF"
            fontSize={12}
            tick={{ fill: '#9CA3AF' }}
            yAxisId="packets"
            orientation="left"
          />
          <YAxis 
            stroke="#9CA3AF"
            fontSize={12}
            tick={{ fill: '#9CA3AF' }}
            yAxisId="traffic"
            orientation="right"
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            yAxisId="packets"
            type="monotone"
            dataKey="packets"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#3B82F6' }}
            name="Packets/sec"
          />
          <Line
            yAxisId="traffic"
            type="monotone"
            dataKey="traffic"
            stroke="#10B981"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#10B981' }}
            name="Traffic MB/s"
          />
        </LineChart>
      </ResponsiveContainer>
      
      {/* Legend */}
      <div className="flex items-center justify-center space-x-6 mt-4 text-sm">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
          <span className="text-dark-text-muted">Packets/sec</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-dark-text-muted">Traffic MB/s</span>
        </div>
      </div>
    </div>
  )
}
