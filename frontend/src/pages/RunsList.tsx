import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useRecentRuns } from '@/hooks/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { parseUTCDateTime } from '@/lib/utils'

export function RunsList() {
  const [skip, setSkip] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useRecentRuns(skip, limit)

  // Data from API is a direct array, not paginated object
  const runs = Array.isArray(data) ? data : []
  const total = runs.length  // Since we get all results from the query
  const hasMore = skip + limit < total

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

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Task Runs</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading runs...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Task Runs</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive">Error loading runs: {error.message}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Task Runs</h1>

      {runs.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">No runs yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {runs.map((run) => (
            <Link key={run.id} to={`/runs/${run.id}`}>
              <Card className="hover:shadow-md transition cursor-pointer">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <CardTitle>Run #{run.id}</CardTitle>
                      <CardDescription>Task ID: {run.task_id}</CardDescription>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(run.status)}`}>
                      {run.status}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-5 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Fetched</p>
                      <p className="text-lg font-bold">{run.rows_fetched || 0}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Inserted</p>
                      <p className="text-lg font-bold">{run.rows_inserted || 0}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Failed</p>
                      <p className="text-lg font-bold text-red-600">{run.error_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Duration</p>
                      <p className="text-lg font-bold">
                        {run.duration_seconds ? `${run.duration_seconds.toFixed(2)}s` : 'N/A'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-muted-foreground">Started</p>
                      <p className="text-sm">
                        {(() => {
                          const date = parseUTCDateTime(run.started_at)
                          return date ? formatDistanceToNow(date, { addSuffix: true }) : 'Pending'
                        })()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="flex justify-between items-center pt-4 border-t">
          <p className="text-sm text-muted-foreground">
            Showing {skip + 1} to {Math.min(skip + limit, total)} of {total} runs
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSkip(Math.max(0, skip - limit))}
              disabled={skip === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSkip(skip + limit)}
              disabled={!hasMore}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
