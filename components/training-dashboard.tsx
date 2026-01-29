"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { 
  Brain, 
  Database, 
  TrendingUp, 
  RefreshCw, 
  Play, 
  CheckCircle, 
  AlertCircle
} from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { format } from "date-fns"

interface TrainingStatistics {
  total_samples: number
  labeled_samples: number
  unlabeled_samples: number
  benign_count: number
  malicious_count: number
  auto_labeled: number
  user_labeled: number
  imported: number
  last_updated: string
}

interface TrainingHistory {
  timestamp: string
  training_samples: number
  validation_samples: number
  test_samples: number
  model_type: string
  test_metrics: {
    accuracy: number
    precision: number
    recall: number
    f1_score: number
  }
  training_time_seconds: number
}

export default function TrainingDashboard() {
  const [statistics, setStatistics] = useState<TrainingStatistics | null>(null)
  const [trainingHistory, setTrainingHistory] = useState<TrainingHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [training, setTraining] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const fetchStatistics = async () => {
    try {
      setError(null)
      const stats = await flaskApi.getTrainingStatistics()
      setStatistics(stats as unknown as TrainingStatistics)
    } catch (err: any) {
      console.error('Error fetching training statistics:', err)
      const errorMsg = err.message || 'Failed to fetch training statistics'
      // Only show error if it's not a network error (backend might not be running)
      if (!errorMsg.includes('Network error') && !errorMsg.includes('fetch')) {
        setError(errorMsg)
      }
    }
  }

  const fetchTrainingHistory = async () => {
    try {
      const history = await flaskApi.getTrainingHistory()
      const list = Array.isArray(history) ? history : (history as { history?: unknown[] }).history ?? []
      setTrainingHistory(list as TrainingHistory[])
    } catch (err) {
      console.error('Error fetching training history:', err)
    }
  }

  const handleTrainModel = async (hyperparameterTuning: boolean = false) => {
    setTraining(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await flaskApi.trainModel({ hyperparameter_tuning: hyperparameterTuning })
      const acc = (result as { training_result?: { test_metrics?: { accuracy?: number } } }).training_result?.test_metrics?.accuracy
      setSuccess(`Model trained successfully! Accuracy: ${((acc ?? 0) * 100).toFixed(2)}%`)
      await fetchStatistics()
      await fetchTrainingHistory()
    } catch (err: any) {
      console.error('Error training model:', err)
      setError(err.message || 'Failed to train model. Make sure you have at least 1000 labeled samples.')
    } finally {
      setTraining(false)
    }
  }

  useEffect(() => {
    fetchStatistics()
    fetchTrainingHistory()
    
    const interval = setInterval(() => {
      fetchStatistics()
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  const getLabelProgress = () => {
    if (!statistics) return 0
    const minRequired = 1000
    return Math.min((statistics.labeled_samples / minRequired) * 100, 100)
  }

  const canTrain = statistics && statistics.labeled_samples >= 1000

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Brain className="h-6 w-6 text-blue-500" />
            ML Training Dashboard
          </h2>
          <p className="text-muted-foreground mt-1">Manage training data and train classification models</p>
        </div>
        <Button onClick={fetchStatistics} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Samples</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_samples}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {statistics.labeled_samples} labeled, {statistics.unlabeled_samples} unlabeled
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Labeled Samples</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">{statistics.labeled_samples}</div>
              <div className="mt-2">
                <Progress value={getLabelProgress()} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {statistics.labeled_samples} / 1000 minimum required
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Class Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Benign</span>
                  <Badge variant="outline" className="bg-green-500/10 text-green-500">
                    {statistics.benign_count}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Malicious</span>
                  <Badge variant="outline" className="bg-red-500/10 text-red-500">
                    {statistics.malicious_count}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Label Sources</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Auto</span>
                  <span className="font-medium">{statistics.auto_labeled}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Manual</span>
                  <span className="font-medium">{statistics.user_labeled}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Imported</span>
                  <span className="font-medium">{statistics.imported}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5 text-blue-500" />
            Model Training
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {success && (
            <div className="p-3 rounded-lg bg-green-500/10 text-green-500 text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              {success}
            </div>
          )}

          <div className="flex items-center gap-4">
            <Button
              onClick={() => handleTrainModel(false)}
              disabled={training || !canTrain}
              className="flex items-center gap-2"
            >
              {training ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Train Model
            </Button>

            <Button
              onClick={() => handleTrainModel(true)}
              disabled={training || !canTrain}
              variant="outline"
              className="flex items-center gap-2"
            >
              {training ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <TrendingUp className="h-4 w-4" />
              )}
              Train with Hyperparameter Tuning
            </Button>

            {!canTrain && (
              <p className="text-sm text-muted-foreground">
                Need at least 1000 labeled samples to train model
              </p>
            )}
          </div>

          {statistics && statistics.labeled_samples < 1000 && (
            <div className="p-3 rounded-lg bg-yellow-500/10 text-yellow-500 text-sm">
              <p>
                Collecting training data... {statistics.labeled_samples} / 1000 samples collected.
                The system is automatically collecting and labeling samples based on signature detection.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {trainingHistory.length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-500" />
              Training History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {trainingHistory.map((history, index) => (
                <div key={index} className="p-4 rounded-lg bg-background border border-border">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline">{history.model_type}</Badge>
                        <span className="text-sm text-muted-foreground">
                          {format(new Date(history.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Training:</span>
                          <span className="ml-2 font-medium">{history.training_samples}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Validation:</span>
                          <span className="ml-2 font-medium">{history.validation_samples}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Test:</span>
                          <span className="ml-2 font-medium">{history.test_samples}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">Training Time</div>
                      <div className="font-medium">{history.training_time_seconds.toFixed(2)}s</div>
                    </div>
                  </div>

                  {history.test_metrics && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 pt-3 border-t border-border">
                      <div>
                        <div className="text-xs text-muted-foreground">Accuracy</div>
                        <div className="text-lg font-bold text-green-500">
                          {(history.test_metrics.accuracy * 100).toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">Precision</div>
                        <div className="text-lg font-bold">
                          {(history.test_metrics.precision * 100).toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">Recall</div>
                        <div className="text-lg font-bold">
                          {(history.test_metrics.recall * 100).toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">F1-Score</div>
                        <div className="text-lg font-bold">
                          {(history.test_metrics.f1_score * 100).toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
