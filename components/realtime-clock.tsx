"use client"

import { useState, useEffect } from "react"

interface RealtimeClockProps {
  className?: string
  showSeconds?: boolean
  showDate?: boolean
}

export default function RealtimeClock({ 
  className = "", 
  showSeconds = true,
  showDate = false 
}: RealtimeClockProps) {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    // Update every second for real-time clock
    const interval = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const timeString = showSeconds 
    ? currentTime.toLocaleTimeString()
    : currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  
  const dateString = currentTime.toLocaleDateString([], { 
    weekday: 'short', 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  })

  return (
    <div className={className}>
      {showDate && (
        <div className="text-xs text-muted-foreground">{dateString}</div>
      )}
      <div className="text-sm text-muted-foreground font-mono">{timeString}</div>
    </div>
  )
}
