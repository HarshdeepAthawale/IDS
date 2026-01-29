"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  BarChart3, 
  RefreshCw,
  AlertTriangle
} from "lucide-react"
import { flaskApi } from "@/lib/flask-api"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts"

interface EvaluationMetrics {
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  specificity: number
  roc_auc: number
  pr_auc: number
  confusion_matrix: {
    true_negatives: number
    false_positives: number
    false_negatives: number
    true_positives: number
    matrix: number[][]
  }
  roc_curve: {
    fpr: number[]
    tpr: number[]
    thresholds: number[]
  }
  pr_curve: {
    precision: number[]
    recall: number[]
    thresholds: number[]
  }
  per_class_metrics: {
    benign: any
    malicious: any
  }
}

interface ModelMetrics {
  model_info: {
    model_type: string
    is_trained: boolean
  }
  feature_importance: Record<string, number>
}

export default function ClassificationMetrics() {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null)
  const [modelMetrics, setModelMetrics] = useState<ModelMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)
    try {
      const evalMetrics = await flaskApi.evaluateModel()
      // Handle different response formats
      const ev = evalMetrics as unknown as { metrics?: EvaluationMetrics; accuracy?: number } & EvaluationMetrics
      if (ev.metrics) {
        setMetrics(ev.metrics)
      } else if (ev.accuracy !== undefined) {
        setMetrics(ev)
      } else {
        throw new Error('Invalid metrics format')
      }
      
      try {
        const modelInfo = await flaskApi.getModelMetrics()
        setModelMetrics(modelInfo as unknown as ModelMetrics)
      } catch (modelErr) {
        // Model metrics are optional, don't fail if they're not available
        console.warn('Could not fetch model metrics:', modelErr)
      }
    } catch (err: any) {
      console.error('Error fetching metrics:', err)
      setError(err.message || 'Failed to fetch metrics. Model may not be trained yet.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [])

  const prepareROCData = () => {
    if (!metrics?.roc_curve) return []
    return metrics.roc_curve.fpr.map((fpr, index) => ({
      fpr: (fpr * 100).toFixed(2),
      tpr: (metrics.roc_curve.tpr[index] * 100).toFixed(2),
    }))
  }

  const preparePRData = () => {
    if (!metrics?.pr_curve) return []
    return metrics.pr_curve.recall.map((recall, index) => ({
      recall: (recall * 100).toFixed(2),
      precision: (metrics.pr_curve.precision[index] * 100).toFixed(2),
    }))
  }

  const getMetricColor = (value: number) => {
    if (value >= 0.85) return "text-green-500"
    if (value >= 0.75) return "text-yellow-500"
    return "text-red-500"
  }

  const getMetricBadgeVariant = (value: number) => {
    if (value >= 0.85) return "default"
    if (value >= 0.75) return "secondary"
    return "destructive"
  }

  if (loading) {
    return (
      <Card className="bg-card border-border">
        <CardContent className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="bg-card border-border">
        <CardContent className="py-12">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-muted-foreground">{error}</p>
            <Button onClick={fetchMetrics} className="mt-4" variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!metrics) {
    return (
      <Card className="bg-card border-border">
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            No metrics available. Train a model first.
          </div>
        </CardContent>
      </Card>
    )
  }

  const confusionMatrix = metrics.confusion_matrix
  const cmData = [
    { name: 'TN', value: confusionMatrix.true_negatives, label: 'True Negatives' },
    { name: 'FP', value: confusionMatrix.false_positives, label: 'False Positives' },
    { name: 'FN', value: confusionMatrix.false_negatives, label: 'False Negatives' },
    { name: 'TP', value: confusionMatrix.true_positives, label: 'True Positives' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-blue-500" />
            Classification Metrics
          </h2>
          <p className="text-muted-foreground mt-1">Model performance evaluation and visualization</p>
        </div>
        <Button onClick={fetchMetrics} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Accuracy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getMetricColor(metrics.accuracy)}`}>
              {(metrics.accuracy * 100).toFixed(2)}%
            </div>
            <Badge variant={getMetricBadgeVariant(metrics.accuracy)} className="mt-2">
              {metrics.accuracy >= 0.85 ? 'Excellent' : metrics.accuracy >= 0.75 ? 'Good' : 'Needs Improvement'}
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Precision</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getMetricColor(metrics.precision)}`}>
              {(metrics.precision * 100).toFixed(2)}%
            </div>
            <Badge variant={getMetricBadgeVariant(metrics.precision)} className="mt-2">
              {metrics.precision >= 0.85 ? 'Excellent' : metrics.precision >= 0.75 ? 'Good' : 'Needs Improvement'}
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Recall</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getMetricColor(metrics.recall)}`}>
              {(metrics.recall * 100).toFixed(2)}%
            </div>
            <Badge variant={getMetricBadgeVariant(metrics.recall)} className="mt-2">
              {metrics.recall >= 0.85 ? 'Excellent' : metrics.recall >= 0.75 ? 'Good' : 'Needs Improvement'}
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">F1-Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getMetricColor(metrics.f1_score)}`}>
              {(metrics.f1_score * 100).toFixed(2)}%
            </div>
            <Badge variant={getMetricBadgeVariant(metrics.f1_score)} className="mt-2">
              {metrics.f1_score >= 0.85 ? 'Excellent' : metrics.f1_score >= 0.75 ? 'Good' : 'Needs Improvement'}
            </Badge>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">ROC-AUC</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getMetricColor(metrics.roc_auc)}`}>
              {metrics.roc_auc.toFixed(3)}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">PR-AUC</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getMetricColor(metrics.pr_auc)}`}>
              {metrics.pr_auc.toFixed(3)}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Specificity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getMetricColor(metrics.specificity)}`}>
              {(metrics.specificity * 100).toFixed(2)}%
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="confusion" className="space-y-4">
        <TabsList>
          <TabsTrigger value="confusion">Confusion Matrix</TabsTrigger>
          <TabsTrigger value="roc">ROC Curve</TabsTrigger>
          <TabsTrigger value="pr">Precision-Recall</TabsTrigger>
          <TabsTrigger value="features">Feature Importance</TabsTrigger>
        </TabsList>

        <TabsContent value="confusion">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Confusion Matrix</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-center">
                  <div className="grid grid-cols-3 gap-2">
                    <div></div>
                    <div className="text-center font-semibold">Predicted Benign</div>
                    <div className="text-center font-semibold">Predicted Malicious</div>
                    
                    <div className="text-center font-semibold flex items-center">Actual Benign</div>
                    <div className="p-4 bg-green-500/20 border-2 border-green-500 rounded text-center">
                      <div className="text-2xl font-bold text-green-500">{confusionMatrix.true_negatives}</div>
                      <div className="text-xs text-muted-foreground mt-1">TN</div>
                    </div>
                    <div className="p-4 bg-red-500/20 border-2 border-red-500 rounded text-center">
                      <div className="text-2xl font-bold text-red-500">{confusionMatrix.false_positives}</div>
                      <div className="text-xs text-muted-foreground mt-1">FP</div>
                    </div>
                    
                    <div className="text-center font-semibold flex items-center">Actual Malicious</div>
                    <div className="p-4 bg-yellow-500/20 border-2 border-yellow-500 rounded text-center">
                      <div className="text-2xl font-bold text-yellow-500">{confusionMatrix.false_negatives}</div>
                      <div className="text-xs text-muted-foreground mt-1">FN</div>
                    </div>
                    <div className="p-4 bg-green-500/20 border-2 border-green-500 rounded text-center">
                      <div className="text-2xl font-bold text-green-500">{confusionMatrix.true_positives}</div>
                      <div className="text-xs text-muted-foreground mt-1">TP</div>
                    </div>
                  </div>
                </div>

                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cmData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value">
                        {cmData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={
                            entry.name === 'TN' || entry.name === 'TP' ? '#22c55e' : '#ef4444'
                          } />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roc">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>ROC Curve (AUC = {metrics.roc_auc.toFixed(3)})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={prepareROCData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="fpr" 
                      label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis 
                      dataKey="tpr"
                      label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip />
                    <Line type="monotone" dataKey="tpr" stroke="#3b82f6" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pr">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Precision-Recall Curve (AUC = {metrics.pr_auc.toFixed(3)})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={preparePRData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="recall" 
                      label={{ value: 'Recall', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis 
                      dataKey="precision"
                      label={{ value: 'Precision', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip />
                    <Line type="monotone" dataKey="precision" stroke="#8b5cf6" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="features">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Feature Importance</CardTitle>
            </CardHeader>
            <CardContent>
              {modelMetrics?.feature_importance ? (
                <div className="space-y-3">
                  {Object.entries(modelMetrics.feature_importance)
                    .sort(([, a], [, b]) => b - a)
                    .map(([feature, importance]) => (
                      <div key={feature} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="capitalize">{feature.replace(/_/g, ' ')}</span>
                          <span className="font-medium">{(importance * 100).toFixed(2)}%</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${importance * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">
                  Feature importance not available for this model type
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
