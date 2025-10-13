// Centralized error handling for the IDS frontend
export class ErrorHandler {
  static handle(error, context = 'Unknown') {
    console.error(`[${context}] Error:`, error)
    
    // Determine error type and user-friendly message
    const errorInfo = this.categorizeError(error)
    
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Details:', {
        context,
        error: error.message || error,
        stack: error.stack,
        timestamp: new Date().toISOString()
      })
    }
    
    return errorInfo
  }
  
  static categorizeError(error) {
    // Network/Connection errors
    if (error.code === 'ECONNREFUSED' || error.message?.includes('connection refused')) {
      return {
        type: 'connection',
        message: 'Unable to connect to backend server',
        severity: 'high',
        suggestion: 'Please check if the backend server is running'
      }
    }
    
    // Timeout errors
    if (error.code === 'ETIMEDOUT' || error.message?.includes('timeout')) {
      return {
        type: 'timeout',
        message: 'Request timed out',
        severity: 'medium',
        suggestion: 'Please try again or check your connection'
      }
    }
    
    // WebSocket connection errors
    if (error.message?.includes('WebSocket') || error.message?.includes('socket')) {
      return {
        type: 'websocket',
        message: 'WebSocket connection failed',
        severity: 'medium',
        suggestion: 'Real-time updates may not work properly'
      }
    }
    
    // API errors
    if (error.response) {
      const status = error.response.status
      
      if (status >= 500) {
        return {
          type: 'server',
          message: 'Server error occurred',
          severity: 'high',
          suggestion: 'Please try again later or contact support'
        }
      } else if (status === 404) {
        return {
          type: 'not_found',
          message: 'Requested resource not found',
          severity: 'medium',
          suggestion: 'The requested data may no longer exist'
        }
      } else if (status === 403) {
        return {
          type: 'permission',
          message: 'Access denied',
          severity: 'high',
          suggestion: 'You may not have permission to access this resource'
        }
      }
    }
    
    // Default error
    return {
      type: 'unknown',
      message: error.message || 'An unexpected error occurred',
      severity: 'medium',
      suggestion: 'Please try refreshing the page'
    }
  }
  
  static createErrorNotification(errorInfo, context) {
    return {
      id: Date.now().toString(),
      type: errorInfo.type,
      message: errorInfo.message,
      suggestion: errorInfo.suggestion,
      severity: errorInfo.severity,
      context,
      timestamp: new Date().toISOString(),
      dismissed: false
    }
  }
}

// Error boundary component for React
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  
  componentDidCatch(error, errorInfo) {
    const errorDetails = ErrorHandler.handle(error, 'React Error Boundary')
    console.error('React Error Boundary caught an error:', errorDetails)
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-dark-bg flex items-center justify-center">
          <div className="text-center max-w-md mx-auto p-6">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-dark-text mb-2">Something went wrong</h2>
            <p className="text-dark-text-muted mb-4">
              An error occurred while rendering this component.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="btn-primary"
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    
    return this.props.children
  }
}
