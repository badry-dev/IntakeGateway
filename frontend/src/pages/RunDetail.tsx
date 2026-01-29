import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useRun } from '@/hooks/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: run, isLoading, error } = useRun(id || '')

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Button variant="outline" size="sm" onClick={() => navigate('/runs')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Runs
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading run details...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="space-y-6">
        <Button variant="outline" size="sm" onClick={() => navigate('/runs')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Runs
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive">Error loading run: {error?.message || 'Run not found'}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-100 text-green-800'
      case 'FAILED':
        return 'bg-red-100 text-red-800'
      case 'RUNNING':
        return 'bg-blue-100 text-blue-800'
      case 'PARTIAL_SUCCESS':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={() => navigate('/runs')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Runs
        </Button>
      </div>

      {/* Run Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Run #{run.id}</CardTitle>
              <CardDescription>Task: {run.task_id}</CardDescription>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(run.status)}`}>
              {run.status}
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Execution Stats */}
          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-1 p-3 bg-secondary rounded">
              <p className="text-sm text-muted-foreground">Records Inserted</p>
              <p className="text-2xl font-bold">{run.records_inserted || 0}</p>
            </div>
            <div className="space-y-1 p-3 bg-secondary rounded">
              <p className="text-sm text-muted-foreground">Records Updated</p>
              <p className="text-2xl font-bold">{run.records_updated || 0}</p>
            </div>
            <div className="space-y-1 p-3 bg-secondary rounded">
              <p className="text-sm text-muted-foreground">Records Failed</p>
              <p className="text-2xl font-bold text-red-600">{run.records_failed || 0}</p>
            </div>
            <div className="space-y-1 p-3 bg-secondary rounded">
              <p className="text-sm text-muted-foreground">Duration</p>
              <p className="text-2xl font-bold">
                {run.execution_time_ms ? `${(run.execution_time_ms / 1000).toFixed(2)}s` : 'N/A'}
              </p>
            </div>
          </div>

          {/* Timing Info */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Started</p>
              <p className="text-sm">
                {new Date(run.started_at).toLocaleString()}
                <br />
                <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
                </span>
              </p>
            </div>
            {run.completed_at && (
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-sm">
                  {new Date(run.completed_at).toLocaleString()}
                  <br />
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(run.completed_at), { addSuffix: true })}
                  </span>
                </p>
              </div>
            )}
            {run.status === 'RUNNING' && (
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="text-sm animate-pulse">⚙️ Running...</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Execution Logs */}
      {run.logs && run.logs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Execution Logs</CardTitle>
            <CardDescription>{run.logs.length} log entries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 bg-secondary p-4 rounded font-mono text-xs max-h-96 overflow-y-auto">
              {run.logs.map((log, idx) => (
                <div key={idx} className="flex gap-2">
                  <span className="text-muted-foreground w-8 flex-shrink-0 text-right">{idx + 1}</span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Row-Level Errors */}
      {run.row_errors && run.row_errors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Row Errors</CardTitle>
            <CardDescription>{run.row_errors.length} rows with errors</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Row Index</th>
                    <th className="text-left p-2">Error Message</th>
                    <th className="text-left p-2">Data</th>
                  </tr>
                </thead>
                <tbody>
                  {run.row_errors.map((err, idx) => (
                    <tr key={idx} className="border-b hover:bg-secondary">
                      <td className="p-2 font-mono text-xs">{err.row_index}</td>
                      <td className="p-2 text-red-600">{err.error_message}</td>
                      <td className="p-2 text-xs">
                        <details>
                          <summary className="cursor-pointer text-blue-600">View Data</summary>
                          <pre className="mt-2 p-2 bg-background rounded text-xs overflow-x-auto">
                            {JSON.stringify(err.row_data, null, 2)}
                          </pre>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No Errors */}
      {(!run.row_errors || run.row_errors.length === 0) && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-green-600 font-medium">✓ No errors - Run completed successfully</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
