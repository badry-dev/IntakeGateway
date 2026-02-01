import { useState } from 'react'
import { format } from 'date-fns'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { useListSchedules, useTasks } from '@/hooks/api'
import { ClockIcon, PlayIcon, PauseIcon, TrashIcon, PlusIcon } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export function Schedules() {
  const navigate = useNavigate()
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(10)
  const [filterActive, setFilterActive] = useState<'all' | 'active' | 'inactive'>('all')
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  // Fetch tasks for the create dialog
  const { data: tasksData } = useTasks(0, 100, true) // Active tasks only
  const tasks = tasksData || []

  const { data: response, isLoading, isError } = useListSchedules(
    skip,
    limit,
    filterActive === 'all' ? undefined : filterActive === 'active'
  )

  const schedules = response?.schedules || []
  const total = response?.total_count || 0
  const pages = Math.ceil(total / limit)
  const currentPage = Math.floor(skip / limit) + 1

  // Get task IDs that already have schedules
  const scheduledTaskIds = new Set(schedules.map(s => s.task_id))
  const availableTasks = tasks.filter(t => !scheduledTaskIds.has(t.id))

  const handleCreateSchedule = (taskId: number) => {
    setShowCreateDialog(false)
    navigate(`/tasks/${taskId}?tab=schedule`)
  }

  const handlePreviousPage = () => {
    if (skip > 0) {
      setSkip(skip - limit)
    }
  }

  const handleNextPage = () => {
    if (skip + limit < total) {
      setSkip(skip + limit)
    }
  }

  if (isError) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-800">Failed to load schedules</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Task Schedules</h1>
          <p className="text-gray-600">Manage automated task execution schedules</p>
        </div>
        
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <PlusIcon className="h-4 w-4 mr-2" />
              Create Schedule
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Schedule for Task</DialogTitle>
              <DialogDescription>
                Select a task to create a schedule. You'll be taken to the task's schedule configuration.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 mt-4">
              {availableTasks.length === 0 ? (
                <p className="text-sm text-gray-600 text-center py-4">
                  All active tasks already have schedules
                </p>
              ) : (
                <div className="space-y-2">
                  {availableTasks.map((task) => (
                    <Button
                      key={task.id}
                      variant="outline"
                      className="w-full justify-start"
                      onClick={() => handleCreateSchedule(task.id)}
                    >
                      <ClockIcon className="h-4 w-4 mr-2 text-gray-500" />
                      <div className="flex-1 text-left">
                        <div className="font-medium">{task.name}</div>
                        <div className="text-xs text-gray-500">{task.dest_table}</div>
                      </div>
                    </Button>
                  ))}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filter Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-end">
            <div className="space-y-2">
              <label className="text-sm font-medium">Filter</label>
              <Select value={filterActive} onValueChange={(v) => {
                setFilterActive(v as 'all' | 'active' | 'inactive')
                setSkip(0)
              }}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Schedules</SelectItem>
                  <SelectItem value="active">Active Only</SelectItem>
                  <SelectItem value="inactive">Inactive Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Items Per Page</label>
              <Select value={limit.toString()} onValueChange={(v) => {
                setLimit(Number(v))
                setSkip(0)
              }}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5</SelectItem>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="ml-auto text-sm text-gray-600">
              Showing {schedules.length > 0 ? skip + 1 : 0} - {Math.min(skip + limit, total)} of {total}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Schedules Table */}
      <Card>
        <CardHeader>
          <CardTitle>Schedules</CardTitle>
          <CardDescription>
            {isLoading ? 'Loading schedules...' : `${total} schedule${total !== 1 ? 's' : ''}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {schedules.length === 0 ? (
            <div className="text-center py-12">
              <ClockIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <p className="text-gray-600 mb-4">
                {isLoading ? 'Loading schedules...' : 'No schedules found'}
              </p>
              {!isLoading && (
                <Button onClick={() => setShowCreateDialog(true)}>
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Create Your First Schedule
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Cron Expression</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Run</TableHead>
                  <TableHead>Next Run</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schedules.map((schedule) => (
                  <TableRow key={schedule.id}>
                    <TableCell>
                      <Link
                        to={`/tasks/${schedule.task_id}`}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        {schedule.task_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs font-mono">
                        {schedule.cron_expression}
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={schedule.is_active ? 'default' : 'secondary'}
                        className="flex w-fit"
                      >
                        {schedule.is_active ? (
                          <>
                            <PlayIcon className="h-3 w-3 mr-1" /> Active
                          </>
                        ) : (
                          <>
                            <PauseIcon className="h-3 w-3 mr-1" /> Inactive
                          </>
                        )}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {schedule.last_run_date ? (
                        <span className="text-sm">
                          {format(new Date(schedule.last_run_date), 'MMM d, yyyy p')}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">Never</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {schedule.next_run_date ? (
                        <span className="text-sm">
                          {format(new Date(schedule.next_run_date), 'MMM d, yyyy p')}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">N/A</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Link to={`/tasks/${schedule.task_id}?tab=schedule`}>
                          <Button variant="outline" size="sm">
                            Edit
                          </Button>
                        </Link>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex gap-2 justify-center pt-4 mt-4 border-t">
              <Button
                variant="outline"
                onClick={handlePreviousPage}
                disabled={skip === 0 || isLoading}
              >
                Previous
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  Page {currentPage} of {pages}
                </span>
              </div>
              <Button
                variant="outline"
                onClick={handleNextPage}
                disabled={skip + limit >= total || isLoading}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
