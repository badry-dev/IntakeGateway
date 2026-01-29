import React from 'react'
import { useRecentRuns, useTasks } from '@/hooks/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'
import { Activity, CheckCircle, AlertCircle, Clock } from 'lucide-react'

export function Dashboard() {
  const { data: recentRuns, isLoading: runsLoading } = useRecentRuns(0, 5)
  const { data: tasks, isLoading: tasksLoading } = useTasks(0, 5)

  const stats = React.useMemo(() => {
    if (!recentRuns) return { running: 0, succeeded: 0, failed: 0 }
    return {
      running: recentRuns.filter(r => r.status === 'RUNNING').length,
      succeeded: recentRuns.filter(r => r.status === 'SUCCESS').length,
      failed: recentRuns.filter(r => r.status === 'FAILED').length,
    }
  }, [recentRuns])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-2">Welcome to API→DB Importer</p>
        </div>
        <Link to="/tasks/new">
          <Button>New Task</Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.running}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Succeeded</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.succeeded}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.failed}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tasks?.length || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
          <CardDescription>Latest 5 task executions</CardDescription>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : recentRuns && recentRuns.length > 0 ? (
            <div className="space-y-4">
              {recentRuns.map(run => (
                <div key={run.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium">Task #{run.task_id}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(run.started_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      run.status === 'SUCCESS' ? 'bg-green-100 text-green-800' :
                      run.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      run.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {run.status}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {run.records_inserted}/{run.records_fetched}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No runs yet</p>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Link to="/tasks" className="block">
            <Button variant="outline" className="w-full justify-start">
              View All Tasks
            </Button>
          </Link>
          <Link to="/runs" className="block">
            <Button variant="outline" className="w-full justify-start">
              View All Runs
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
