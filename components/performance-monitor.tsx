"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Activity, Database, Zap, Clock, TrendingUp, RefreshCw } from "lucide-react"
import { frontendCache } from "@/lib/cache"
import { config } from "@/lib/config"
import { getAverageResponseTime, getResponseTimeStats } from "@/lib/flask-api"

interface PerformanceMetrics {
  cacheHitRate: number
  totalRequests: number
  avgResponseTime: number
  memoryUsage: number
  pollingInterval: number
  lastUpdate: string
}

export default function PerformanceMonitor() {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    cacheHitRate: 0,
    totalRequests: 0,
    avgResponseTime: 0,
    memoryUsage: 0,
    pollingInterval: 0,
    lastUpdate: new Date().toISOString()
  })
  const [isVisible, setIsVisible] = useState(false)

  const updateMetrics = () => {
    const cacheStats = frontendCache.getStats()
    const responseTimeStats = getResponseTimeStats()
    const now = new Date()
    
    setMetrics({
      cacheHitRate: cacheStats.valid > 0 ? (cacheStats.valid / cacheStats.total) * 100 : 0,
      totalRequests: cacheStats.total,
      avgResponseTime: responseTimeStats.avg > 0 ? responseTimeStats.avg : 0, // Real response time from API calls
      memoryUsage: cacheStats.memoryUsage,
      pollingInterval: Math.max(config.polling.dashboard, 20000),
      lastUpdate: now.toISOString()
    })
  }

  useEffect(() => {
    updateMetrics()
    const interval = setInterval(updateMetrics, 10000) // Update every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const performanceScore = useMemo(() => {
    const cacheScore = Math.min(metrics.cacheHitRate * 0.4, 40)
    const speedScore = Math.max(40 - (metrics.avgResponseTime / 10), 0)
    const efficiencyScore = Math.min(20 - (metrics.memoryUsage / 1000), 20)
    
    return Math.round(cacheScore + speedScore + efficiencyScore)
  }, [metrics])

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500"
    if (score >= 60) return "text-yellow-500"
    return "text-red-500"
  }

  const getScoreBadgeVariant = (score: number) => {
    if (score >= 80) return "default" as const
    if (score >= 60) return "secondary" as const
    return "destructive" as const
  }

  if (!isVisible) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          onClick={() => setIsVisible(true)}
          variant="outline"
          size="sm"
          className="flex items-center gap-2 shadow-lg"
        >
          <Activity className="h-4 w-4" />
          Performance
        </Button>
      </div>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-80">
      <Card className="bg-card border-border shadow-lg">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-500" />
              Performance Monitor
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsVisible(false)}
              className="h-6 w-6 p-0"
            >
              ×
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Performance Score */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Performance Score</span>
            <Badge variant={getScoreBadgeVariant(performanceScore)} className="text-xs">
              <span className={getScoreColor(performanceScore)}>
                {performanceScore}/100
              </span>
            </Badge>
          </div>

          {/* Cache Hit Rate */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Cache Hit Rate</span>
            <Badge variant="outline" className="text-xs">
              {metrics.cacheHitRate.toFixed(1)}%
            </Badge>
          </div>

          {/* Total Requests */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Cached Requests</span>
            <Badge variant="outline" className="text-xs">
              {metrics.totalRequests}
            </Badge>
          </div>

          {/* Memory Usage */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Cache Size</span>
            <Badge variant="outline" className="text-xs">
              {(metrics.memoryUsage / 1024).toFixed(1)}KB
            </Badge>
          </div>

          {/* Polling Interval */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Polling Interval</span>
            <Badge variant="outline" className="text-xs">
              {metrics.pollingInterval / 1000}s
            </Badge>
          </div>

          {/* Optimizations Applied */}
          <div className="pt-2 border-t border-border">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-3 w-3 text-green-500" />
              <span className="text-xs font-medium text-green-500">Optimizations Active</span>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Database className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-muted-foreground">Database Indexing</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-muted-foreground">Response Caching</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-muted-foreground">React Memoization</span>
              </div>
              <div className="flex items-center gap-2">
                <RefreshCw className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-muted-foreground">Optimized Polling</span>
              </div>
            </div>
          </div>

          {/* Last Update */}
          <div className="text-xs text-muted-foreground text-center pt-2 border-t border-border">
            Last updated: {new Date(metrics.lastUpdate).toLocaleTimeString()}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
