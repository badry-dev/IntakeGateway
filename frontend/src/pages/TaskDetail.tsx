import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTask, useUpdateTask, useDeleteTask } from '@/hooks/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Edit2, Trash2, Copy } from 'lucide-react'
import { Task, TaskFormData } from '@/types'
import { formatLocalDateTime } from '@/lib/utils'

export function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: task, isLoading, error } = useTask(id || '')
  const updateTaskMutation = useUpdateTask()
  const deleteTaskMutation = useDeleteTask()

  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [formData, setFormData] = useState<TaskFormData>({
    name: '',
    description: '',
    endpoint_path: '',
    http_method: 'GET',
    dest_table: '',
    headers_json: {},
    body_json: {},
    batch_size: 500,
    is_active: true,
  })

  // Initialize form when task loads
  React.useEffect(() => {
    if (task) {
      setFormData({
        name: task.name,
        description: task.description || '',
        endpoint_path: task.endpoint_path,
        http_method: task.http_method,
        dest_table: task.dest_table,
        headers_json: task.headers_json || {},
        body_json: task.body_json || {},
        batch_size: task.batch_size,
        is_active: task.is_active,
      })
    }
  }, [task])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Button variant="outline" size="sm" onClick={() => navigate('/tasks')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Tasks
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading task details...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="space-y-6">
        <Button variant="outline" size="sm" onClick={() => navigate('/tasks')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Tasks
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive">Error loading task: {error?.message || 'Task not found'}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleSaveEdit = async () => {
    try {
      await updateTaskMutation.mutateAsync({
        id: task.id,
        data: formData,
      })
      setIsEditOpen(false)
    } catch (err) {
      console.error('Failed to update task:', err)
    }
  }

  const handleDelete = async () => {
    try {
      await deleteTaskMutation.mutateAsync(task.id)
      navigate('/tasks')
    } catch (err) {
      console.error('Failed to delete task:', err)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={() => navigate('/tasks')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Tasks
        </Button>
        <div className="flex gap-2">
          <Button 
            size="sm" 
            onClick={() => setIsEditOpen(true)}
            className="gap-2"
          >
            <Edit2 className="h-4 w-4" />
            Edit
          </Button>
          <Button 
            size="sm" 
            variant="destructive"
            onClick={() => setIsDeleteOpen(true)}
            className="gap-2"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Task Info */}
      <Card>
        <CardHeader>
          <CardTitle>{task.name}</CardTitle>
          {task.description && <CardDescription>{task.description}</CardDescription>}
        </CardHeader>
        <CardContent className="space-y-6">
          {/* API Configuration */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Method</Label>
              <p className="text-lg font-mono bg-secondary p-2 rounded">{task.http_method}</p>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Table</Label>
              <p className="text-lg font-mono bg-secondary p-2 rounded">{task.dest_table}</p>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium text-muted-foreground">Endpoint URL</Label>
            <div className="flex items-center gap-2">
              <p className="text-sm break-all flex-1 bg-secondary p-3 rounded font-mono">{task.endpoint_path}</p>
              <button
                onClick={() => navigator.clipboard.writeText(task.endpoint_path)}
                className="p-2 hover:bg-secondary rounded"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Headers */}
          {Object.keys(task.headers_json || {}).length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Headers</Label>
              <div className="bg-secondary p-3 rounded font-mono text-sm space-y-1">
                {Object.entries(task.headers_json || {}).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-blue-600">{key}</span>
                    <span className="text-muted-foreground">: </span>
                    <span>{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Body */}
          {Object.keys(task.body_json || {}).length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Request Body</Label>
              <div className="bg-secondary p-3 rounded font-mono text-sm">
                <pre>{JSON.stringify(task.body_json, null, 2)}</pre>
              </div>
            </div>
          )}

          {/* Status */}
          <div className="pt-4 border-t">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-sm text-muted-foreground">Status</Label>
                <p className={`text-sm font-medium ${task.is_active ? 'text-green-600' : 'text-yellow-600'}`}>
                  {task.is_active ? '✓ Active' : '○ Inactive'}
                </p>
              </div>
              <div className="space-y-1">
                <Label className="text-sm text-muted-foreground">Created</Label>
                <p className="text-sm">
                  {task.created_at ? new Date(task.created_at).toLocaleString('en-US', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: true
                  }) : 'N/A'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      {isEditOpen && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => setIsEditOpen(false)}
        >
          <Card 
            className="w-full max-w-2xl max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader className="border-b">
              <CardTitle>Edit Task</CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Task Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Sync Users"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe what this task does"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="endpoint_path">Endpoint URL *</Label>
                <Input
                  id="endpoint_path"
                  value={formData.endpoint_path}
                  onChange={(e) => setFormData({ ...formData, endpoint_path: e.target.value })}
                  placeholder="https://api.example.com/users"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="http_method">HTTP Method *</Label>
                  <select
                    id="http_method"
                    value={formData.http_method}
                    onChange={(e) => setFormData({ ...formData, http_method: e.target.value as 'GET' | 'POST' | 'PUT' | 'PATCH' })}
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  >
                    <option>GET</option>
                    <option>POST</option>
                    <option>PUT</option>
                    <option>PATCH</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dest_table">Table Name *</Label>
                  <Input
                    id="dest_table"
                    value={formData.dest_table}
                    onChange={(e) => setFormData({ ...formData, dest_table: e.target.value })}
                    placeholder="users"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => setIsEditOpen(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveEdit}
                  disabled={updateTaskMutation.isPending}
                  className="flex-1"
                >
                  {updateTaskMutation.isPending ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {isDeleteOpen && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => setIsDeleteOpen(false)}
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
                Are you sure you want to delete "<strong>{task.name}</strong>"? This will remove the task and all associated run history.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setIsDeleteOpen(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
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
