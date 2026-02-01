import { useState, useEffect } from 'react'
import { format, addMinutes } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TaskSchedule, ScheduleCreate } from '@/types'

// Simple cron validator - validates basic cron format (not full validation)
function validateCron(expression: string): boolean {
  const parts = expression.trim().split(/\s+/)
  if (parts.length !== 5) return false
  
  // Basic validation: each part should be *, a number, or contain valid cron syntax
  for (let i = 0; i < 5; i++) {
    const part = parts[i]
    if (part === '*') continue
    if (part.match(/^\d+$/)) continue
    if (part.includes(',') || part.includes('-') || part.includes('/')) continue
    return false
  }
  return true
}

// Calculate approximate next run time (simplified - just adds some time)
function getNextRunTime(cron: string): Date | null {
  if (!validateCron(cron)) return null
  
  // For display purposes, just add appropriate time
  const parts = cron.split(/\s+/)
  const minute = parseInt(parts[0])
  const hour = parseInt(parts[1])
  
  if (!isNaN(hour) && !isNaN(minute)) {
    const now = new Date()
    const nextRun = new Date(now)
    nextRun.setHours(hour, minute, 0, 0)
    
    if (nextRun <= now) {
      nextRun.setDate(nextRun.getDate() + 1)
    }
    return nextRun
  }
  
  return addMinutes(new Date(), 5)
}

interface ScheduleEditorProps {
  taskId?: number
  schedule?: TaskSchedule
  onSave: (data: ScheduleCreate) => Promise<void>
  onDelete?: () => Promise<void>
  isLoading?: boolean
  isEditing?: boolean
}

// Cron presets
const CRON_PRESETS = {
  hourly: { label: 'Every Hour', expression: '0 * * * *' },
  daily_2am: { label: 'Daily at 2:00 AM', expression: '0 2 * * *' },
  daily_noon: { label: 'Daily at 12:00 PM', expression: '0 12 * * *' },
  weekly_sunday: { label: 'Weekly (Sunday at 2:00 AM)', expression: '0 2 * * 0' },
  weekly_monday: { label: 'Weekly (Monday at 2:00 AM)', expression: '0 2 * * 1' },
  monthly_1st: { label: 'Monthly (1st at 2:00 AM)', expression: '0 2 1 * *' },
  every_6h: { label: 'Every 6 Hours', expression: '0 */6 * * *' },
  every_30m: { label: 'Every 30 Minutes', expression: '*/30 * * * *' },
}

export function ScheduleEditor({
  taskId,
  schedule,
  onSave,
  onDelete,
  isLoading = false,
  isEditing = false,
}: ScheduleEditorProps) {
  const [cron, setCron] = useState(schedule?.cron_expression || '')
  const [isActive, setIsActive] = useState(schedule?.is_active ?? true)
  const [cronError, setCronError] = useState<string | null>(null)
  const [nextRun, setNextRun] = useState<Date | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  // Calculate next run date when cron expression changes
  useEffect(() => {
    if (!cron) {
      setNextRun(null)
      setCronError(null)
      return
    }

    if (validateCron(cron)) {
      const next = getNextRunTime(cron)
      setNextRun(next)
      setCronError(null)
    } else {
      setCronError('Invalid cron expression (use format: minute hour day month dayOfWeek)')
      setNextRun(null)
    }
  }, [cron])

  const handlePresetSelect = (presetKey: keyof typeof CRON_PRESETS | string) => {
    if (presetKey in CRON_PRESETS) {
      setCron(CRON_PRESETS[presetKey as keyof typeof CRON_PRESETS].expression)
    }
  }

  const handleSave = async () => {
    if (!cron) {
      setCronError('Cron expression is required')
      return
    }

    if (cronError) {
      return
    }

    setIsSaving(true)
    try {
      await onSave({
        cron_expression: cron,
        is_active: isActive,
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!onDelete) return

    setIsSaving(true)
    try {
      await onDelete()
    } finally {
      setIsSaving(false)
      setDeleteConfirm(false)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Schedule Configuration</CardTitle>
        <CardDescription>
          {isEditing ? 'Update the schedule for this task' : 'Set up automated task execution'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Cron Expression Input */}
        <div className="space-y-2">
          <Label htmlFor="cron">Cron Expression</Label>
          <Input
            id="cron"
            placeholder="0 2 * * * (Daily at 2 AM)"
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            className={cronError ? 'border-red-500' : ''}
            disabled={isLoading || isSaving}
          />
          {cronError && <p className="text-sm text-red-500">{cronError}</p>}
          <p className="text-xs text-gray-500">
            Format: minute hour day-of-month month day-of-week
          </p>
          <p className="text-xs text-gray-500">
            Learn more: <a href="https://crontab.guru" target="_blank" rel="noopener noreferrer" className="underline">crontab.guru</a>
          </p>
        </div>

        {/* Preset Selection */}
        <div className="space-y-2">
          <Label htmlFor="preset">Quick Presets</Label>
          <Select onValueChange={(key) => handlePresetSelect(key as keyof typeof CRON_PRESETS)}>
            <SelectTrigger id="preset" disabled={isLoading || isSaving}>
              <SelectValue placeholder="Select a preset..." />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(CRON_PRESETS).map(([key, value]) => (
                <SelectItem key={key} value={key}>
                  {value.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Active Toggle */}
        <div className="flex items-center space-x-2">
          <input
            id="active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            disabled={isLoading || isSaving}
            className="h-4 w-4 rounded border-gray-300"
          />
          <Label htmlFor="active" className="font-normal cursor-pointer">
            Active
          </Label>
        </div>

        {/* Next Run Preview */}
        {nextRun && !cronError && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <p className="text-sm font-semibold text-blue-900">Next Run</p>
            <p className="text-sm text-blue-800">
              {format(nextRun, 'PPPPp')}
            </p>
          </div>
        )}

        {/* Schedule Info (if editing) */}
        {isEditing && schedule && (
          <div className="bg-gray-50 border border-gray-200 rounded-md p-3 space-y-2">
            <p className="text-sm text-gray-600">
              <span className="font-semibold">Created:</span>{' '}
              {format(new Date(schedule.created_at), 'PPp')}
            </p>
            {schedule.last_run_date && (
              <p className="text-sm text-gray-600">
                <span className="font-semibold">Last Run:</span>{' '}
                {format(new Date(schedule.last_run_date), 'PPp')}
              </p>
            )}
            {schedule.next_run_date && (
              <p className="text-sm text-gray-600">
                <span className="font-semibold">Next Run:</span>{' '}
                {format(new Date(schedule.next_run_date), 'PPp')}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-4">
          <Button
            onClick={handleSave}
            disabled={isLoading || isSaving || !cron || !!cronError}
            className="flex-1"
          >
            {isSaving ? 'Saving...' : isEditing ? 'Update Schedule' : 'Create Schedule'}
          </Button>

          {isEditing && onDelete && (
            <>
              {!deleteConfirm ? (
                <Button
                  onClick={() => setDeleteConfirm(true)}
                  variant="outline"
                  disabled={isLoading || isSaving}
                  className="text-red-600 hover:text-red-700"
                >
                  Delete
                </Button>
              ) : (
                <>
                  <Button
                    onClick={handleDelete}
                    variant="destructive"
                    disabled={isSaving}
                    className="flex-1"
                  >
                    {isSaving ? 'Deleting...' : 'Confirm Delete'}
                  </Button>
                  <Button
                    onClick={() => setDeleteConfirm(false)}
                    variant="outline"
                    disabled={isSaving}
                  >
                    Cancel
                  </Button>
                </>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
