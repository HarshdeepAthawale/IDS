'use client'

import { useState, useEffect } from 'react'

export default function ErrorNotification({ error, onDismiss }) {
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    if (error) {
      setIsVisible(true)
      
      // Auto-dismiss after 10 seconds for medium/low severity
      if (error.severity !== 'high' && error.severity !== 'critical') {
        const timer = setTimeout(() => {
          handleDismiss()
        }, 10000)
        
        return () => clearTimeout(timer)
      }
    }
  }, [error])

  const handleDismiss = () => {
    setIsVisible(false)
    setTimeout(() => {
      onDismiss()
    }, 300) // Wait for animation to complete
  }

  if (!error || !isVisible) return null

  const getErrorIcon = (type) => {
    const icons = {
      connection: '🔌',
      timeout: '⏱️',
      websocket: '📡',
      server: '🖥️',
      not_found: '🔍',
      permission: '🔒',
      unknown: '⚠️'
    }
    return icons[type] || icons.unknown
  }

  const getErrorStyles = (severity) => {
    const styles = {
      critical: 'bg-red-900/30 border-red-700/50 text-red-300',
      high: 'bg-red-900/20 border-red-800/30 text-red-400',
      medium: 'bg-yellow-900/20 border-yellow-800/30 text-yellow-400',
      low: 'bg-blue-900/20 border-blue-800/30 text-blue-400'
    }
    return styles[severity] || styles.medium
  }

  return (
    <div className={`fixed top-4 right-4 z-50 max-w-md transition-all duration-300 ${
      isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-full'
    }`}>
      <div className={`border rounded-lg p-4 shadow-lg ${getErrorStyles(error.severity)}`}>
        <div className="flex items-start space-x-3">
          <div className="text-xl">{getErrorIcon(error.type)}</div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-sm font-semibold">
                {error.type?.replace('_', ' ').toUpperCase() || 'ERROR'}
              </h4>
              <button
                onClick={handleDismiss}
                className="text-current opacity-60 hover:opacity-100 transition-opacity"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <p className="text-sm mb-2">{error.message}</p>
            
            {error.suggestion && (
              <p className="text-xs opacity-80">{error.suggestion}</p>
            )}
            
            {error.context && (
              <p className="text-xs opacity-60 mt-1">
                Context: {error.context}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function ErrorNotificationContainer({ errors, onDismissError }) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {errors.map((error) => (
        <ErrorNotification
          key={error.id}
          error={error}
          onDismiss={() => onDismissError(error.id)}
        />
      ))}
    </div>
  )
}
