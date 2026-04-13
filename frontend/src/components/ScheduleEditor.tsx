import { useState, useEffect } from 'react'
import { format, addMinutes } from 'date-fns'
import { Button, Input, Select, Switch, Card, Space, Typography, Alert } from 'antd'
import { TaskSchedule, ScheduleCreate } from '@/types'

const { Text } = Typography

function validateCron(expression: string): boolean {
  const parts = expression.trim().split(/\s+/)
  if (parts.length !== 5) return false
  for (const part of parts) {
    if (part === '*') continue
    if (part.match(/^\d+$/)) continue
    if (part.includes(',') || part.includes('-') || part.includes('/')) continue
    return false
  }
  return true
}

function getNextRunTime(cron: string): Date | null {
  if (!validateCron(cron)) return null
  const parts = cron.split(/\s+/)
  const minute = parseInt(parts[0])
  const hour = parseInt(parts[1])
  if (!isNaN(hour) && !isNaN(minute)) {
    const now = new Date()
    const nextRun = new Date(now)
    nextRun.setHours(hour, minute, 0, 0)
    if (nextRun <= now) nextRun.setDate(nextRun.getDate() + 1)
    return nextRun
  }
  return addMinutes(new Date(), 5)
}

const CRON_PRESETS = [
  { value: '0 * * * *', label: 'Every Hour' },
  { value: '0 2 * * *', label: 'Daily at 2:00 AM' },
  { value: '0 12 * * *', label: 'Daily at 12:00 PM' },
  { value: '0 2 * * 0', label: 'Weekly (Sunday at 2:00 AM)' },
  { value: '0 2 * * 1', label: 'Weekly (Monday at 2:00 AM)' },
  { value: '0 2 1 * *', label: 'Monthly (1st at 2:00 AM)' },
  { value: '0 */6 * * *', label: 'Every 6 Hours' },
  { value: '*/30 * * * *', label: 'Every 30 Minutes' },
]

interface ScheduleEditorProps {
  taskId?: number
  schedule?: TaskSchedule
  onSave: (data: ScheduleCreate) => Promise<void>
  onDelete?: () => Promise<void>
  isLoading?: boolean
  isEditing?: boolean
}

export function ScheduleEditor({ schedule, onSave, onDelete, isLoading = false, isEditing = false }: ScheduleEditorProps) {
  const [cron, setCron] = useState(schedule?.cron_expression || '')
  const [isActive, setIsActive] = useState(schedule?.is_active ?? true)
  const [cronError, setCronError] = useState<string | null>(null)
  const [nextRun, setNextRun] = useState<Date | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  useEffect(() => {
    if (!cron) { setNextRun(null); setCronError(null); return }
    if (validateCron(cron)) { setNextRun(getNextRunTime(cron)); setCronError(null) }
    else { setCronError('Invalid cron expression (format: minute hour day month dayOfWeek)'); setNextRun(null) }
  }, [cron])

  const handleSave = async () => {
    if (!cron) { setCronError('Cron expression is required'); return }
    if (cronError) return
    setIsSaving(true)
    try { await onSave({ cron_expression: cron, is_active: isActive }) }
    finally { setIsSaving(false) }
  }

  const handleDelete = async () => {
    if (!onDelete) return
    setIsSaving(true)
    try { await onDelete() } finally { setIsSaving(false); setDeleteConfirm(false) }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div>
        <Text strong>Cron Expression</Text>
        <Input
          placeholder="0 2 * * * (Daily at 2 AM)"
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          status={cronError ? 'error' : undefined}
          disabled={isLoading || isSaving}
        />
        {cronError && <Text type="danger" style={{ fontSize: 12 }}>{cronError}</Text>}
        <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          Format: minute hour day-of-month month day-of-week |{' '}
          <a href="https://crontab.guru" target="_blank" rel="noopener noreferrer">crontab.guru</a>
        </div>
      </div>

      <div>
        <Text strong>Quick Presets</Text>
        <Select
          placeholder="Select a preset..."
          onChange={(v) => setCron(v)}
          options={CRON_PRESETS}
          disabled={isLoading || isSaving}
          style={{ width: '100%' }}
        />
      </div>

      <Space>
        <Switch checked={isActive} onChange={setIsActive} disabled={isLoading || isSaving} />
        <Text>Active</Text>
      </Space>

      {nextRun && !cronError && (
        <Alert message={`Next Run: ${format(nextRun, 'PPPPp')}`} type="info" showIcon />
      )}

      {isEditing && schedule && (
        <Card size="small" style={{ background: '#fafafa' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>Created: {format(new Date(schedule.created_at), 'PPp')}</Text>
          {schedule.last_run_date && <><br /><Text type="secondary" style={{ fontSize: 12 }}>Last Run: {format(new Date(schedule.last_run_date), 'PPp')}</Text></>}
          {schedule.next_run_date && <><br /><Text type="secondary" style={{ fontSize: 12 }}>Next Run: {format(new Date(schedule.next_run_date), 'PPp')}</Text></>}
        </Card>
      )}

      <Space>
        <Button type="primary" onClick={handleSave} loading={isSaving} disabled={isLoading || !cron || !!cronError}>
          {isEditing ? 'Update Schedule' : 'Create Schedule'}
        </Button>
        {isEditing && onDelete && !deleteConfirm && (
          <Button danger onClick={() => setDeleteConfirm(true)} disabled={isLoading || isSaving}>Delete</Button>
        )}
        {deleteConfirm && (
          <>
            <Button type="primary" danger onClick={handleDelete} loading={isSaving}>Confirm Delete</Button>
            <Button onClick={() => setDeleteConfirm(false)} disabled={isSaving}>Cancel</Button>
          </>
        )}
      </Space>
    </Space>
  )
}
