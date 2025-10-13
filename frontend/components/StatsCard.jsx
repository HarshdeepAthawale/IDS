'use client'

import { useState, useEffect } from 'react'

export default function StatsCard({ 
  title, 
  value, 
  unit, 
  icon, 
  color = 'blue',
  trend = null,
  subtitle = null 
}) {
  const [displayValue, setDisplayValue] = useState(0)

  // Animate counter when value changes
  useEffect(() => {
    const startValue = displayValue
    const endValue = typeof value === 'number' ? value : 0
    const duration = 1000
    const startTime = Date.now()

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      
      // Easing function for smooth animation
      const easeOutCubic = 1 - Math.pow(1 - progress, 3)
      const currentValue = startValue + (endValue - startValue) * easeOutCubic
      
      setDisplayValue(currentValue)

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [value])

  const getColorClasses = (color) => {
    const colorMap = {
      blue: {
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/20',
        text: 'text-blue-400',
        icon: 'text-blue-500'
      },
      red: {
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        text: 'text-red-400',
        icon: 'text-red-500'
      },
      green: {
        bg: 'bg-green-500/10',
        border: 'border-green-500/20',
        text: 'text-green-400',
        icon: 'text-green-500'
      },
      yellow: {
        bg: 'bg-yellow-500/10',
        border: 'border-yellow-500/20',
        text: 'text-yellow-400',
        icon: 'text-yellow-500'
      },
      purple: {
        bg: 'bg-purple-500/10',
        border: 'border-purple-500/20',
        text: 'text-purple-400',
        icon: 'text-purple-500'
      }
    }
    return colorMap[color] || colorMap.blue
  }

  const colors = getColorClasses(color)

  const formatValue = (val) => {
    if (typeof val !== 'number') return val
    
    if (val >= 1000000) {
      return (val / 1000000).toFixed(1) + 'M'
    } else if (val >= 1000) {
      return (val / 1000).toFixed(1) + 'K'
    } else if (val % 1 !== 0) {
      return val.toFixed(1)
    }
    return Math.round(val)
  }

  const getTrendIcon = (trend) => {
    if (!trend) return null
    
    if (trend > 0) {
      return (
        <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      )
    } else if (trend < 0) {
      return (
        <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
        </svg>
      )
    }
    return (
      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
      </svg>
    )
  }

  return (
    <div className={`card ${colors.bg} ${colors.border} border-l-4`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <span className={`text-lg ${colors.icon}`}>{icon}</span>
            <h3 className="text-sm font-medium text-dark-text-muted">{title}</h3>
            {trend !== null && getTrendIcon(trend)}
          </div>
          
          <div className="flex items-baseline space-x-2">
            <span className={`text-2xl font-bold ${colors.text}`}>
              {formatValue(displayValue)}
            </span>
            {unit && (
              <span className="text-sm text-dark-text-muted">{unit}</span>
            )}
          </div>
          
          {subtitle && (
            <p className="text-xs text-dark-text-muted mt-1">{subtitle}</p>
          )}
        </div>
        
        {/* Optional decorative element */}
        <div className={`w-12 h-12 ${colors.bg} rounded-full flex items-center justify-center opacity-20`}>
          <span className={`text-xl ${colors.icon}`}>{icon}</span>
        </div>
      </div>
    </div>
  )
}
