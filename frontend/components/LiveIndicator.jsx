'use client'

export default function LiveIndicator({ status = 'offline' }) {
  const getStatusConfig = (status) => {
    switch (status) {
      case 'online':
      case 'connected':
        return {
          color: 'bg-green-500',
          pulse: 'animate-pulse-slow',
          label: 'Live',
          textColor: 'text-green-400'
        }
      case 'connecting':
        return {
          color: 'bg-yellow-500',
          pulse: 'animate-bounce-slow',
          label: 'Connecting',
          textColor: 'text-yellow-400'
        }
      case 'offline':
      case 'disconnected':
      default:
        return {
          color: 'bg-red-500',
          pulse: '',
          label: 'Offline',
          textColor: 'text-red-400'
        }
    }
  }

  const config = getStatusConfig(status)

  return (
    <div className="flex items-center space-x-2">
      <div className={`w-3 h-3 rounded-full ${config.color} ${config.pulse}`} />
      <span className={`text-sm font-medium ${config.textColor}`}>
        {config.label}
      </span>
    </div>
  )
}
