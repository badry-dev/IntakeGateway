import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTasks, useTriggerRun, useDeleteTask, useListSchedules } from '@/hooks/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Play, Edit2, Trash2, Plus, Clock } from 'lucide-react'

export function TaskList() {
  const [skip, setSkip] = useState(0)
  const limit = 10

  const { data, isLoading, error } = useTasks(skip, limit, true)
  const { data: schedulesResponse } = useListSchedules(0, 1000)
  const triggerRunMutation = useTriggerRun()
  const deleteTaskMutation = useDeleteTask()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)

  // Create a map of taskId -> schedule for quick lookup
  const schedulesByTaskId = React.useMemo(() => {
    const map: Record<number, any> = {}
    if (schedulesResponse?.items) {
      schedulesResponse.items.forEach((schedule) => {
        map[schedule.task_id] = schedule
      })
    }
    return map
  }, [schedulesResponse])

  const tasks = data || []
  const total = tasks.length
  const hasMore = tasks.length === limit

  const handleDelete = async (taskId: number) => {
    try {
      await deleteTaskMutation.mutateAsync(taskId)
      setDeleteOpen(false)
      setSelectedTaskId(null)
    } catch (err) {
      console.error('Failed to delete task:', err)
    }
  }

  const handleRun = async (taskId: number) => {
    try {
      await triggerRunMutation.mutateAsync(taskId)
      alert('Task run triggered successfully!')
    } catch (err) {
      console.error('Failed to trigger run:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Tasks</h1>
          <Link to="/tasks/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New Task
            </Button>
          </Link>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading tasks...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Tasks</h1>
          <Link to="/tasks/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New Task
            </Button>
          </Link>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive">Error loading tasks: {error.message}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Tasks</h1>
        <Link to="/tasks/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Task
          </Button>
        </Link>
      </div>

      {/* Task List */}
      {tasks.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground mb-4">No tasks yet</p>
            <Link to="/tasks/new">
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Create Your First Task
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {tasks.map((task) => (
            <Card key={task.id} className="hover:shadow-md transition">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Link to={`/tasks/${task.id}`}>
                        <CardTitle className="hover:text-primary cursor-pointer">
                          {task.name}
                        </CardTitle>
                      </Link>
                      {schedulesByTaskId[task.id] && (
                        <Link to={`/schedules?task=${task.id}`} title={`Schedule: ${schedulesByTaskId[task.id].cron_expression}`}>
                          <Clock 
                            className={`h-4 w-4 cursor-pointer ${
                              schedulesByTaskId[task.id].is_active 
                                ? 'text-green-600' 
                                : 'text-gray-400'
                            }`}
                          />
                        </Link>
                      )}
                    </div>
                    {task.description && (
                      <CardDescription>{task.description}</CardDescription>
                    )}
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      task.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {task.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Method</p>
                    <p className="font-mono font-bold">{task.http_method}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Table</p>
                    <p className="font-mono font-bold">{task.dest_table}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Endpoint</p>
                    <p className="font-mono text-xs truncate">{task.endpoint_path}</p>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRun(task.id)}
                    disabled={triggerRunMutation.isPending}
                    className="gap-2"
                  >
                    <Play className="h-4 w-4" />
                    Run
                  </Button>
                  <Link to={`/tasks/${task.id}`}>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-2"
                    >
                      <Edit2 className="h-4 w-4" />
                      Edit
                    </Button>
                  </Link>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedTaskId(task.id)
                      setDeleteOpen(true)
                    }}
                    className="gap-2"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="flex justify-between items-center pt-4 border-t">
          <p className="text-sm text-muted-foreground">
            Showing {skip + 1} to {Math.min(skip + limit, total)} of {total} tasks
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

      {/* Delete Confirmation Dialog */}
      {deleteOpen && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => setDeleteOpen(false)}
        >
          <Card 
            className="w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader>
              <CardTitle>Delete Task</CardTitle>
              <CardDescription>This action cannot be undone</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete this task? All associated run history will also be deleted.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setDeleteOpen(false)
                    setSelectedTaskId(null)
                  }}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => selectedTaskId && handleDelete(selectedTaskId)}
                  disabled={deleteTaskMutation.isPending}
                  className="flex-1"
                >
                  {deleteTaskMutation.isPending ? 'Deleting...' : 'Delete'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

