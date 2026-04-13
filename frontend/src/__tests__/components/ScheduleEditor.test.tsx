import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ScheduleEditor } from '@/components/ScheduleEditor'

describe('ScheduleEditor', () => {
  const mockOnSave = vi.fn()
  const mockOnDelete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders form with cron input field', () => {
    render(<ScheduleEditor taskId={1} onSave={mockOnSave} />)
    expect(screen.getByPlaceholderText(/0 2 \* \* \*/)).toBeInTheDocument()
    expect(screen.getByText('Create Schedule')).toBeInTheDocument()
  })

  it('validates required cron expression', async () => {
    const user = userEvent.setup()
    render(<ScheduleEditor taskId={1} onSave={mockOnSave} />)

    await user.click(screen.getByText('Create Schedule'))
    expect(screen.getByText('Cron expression is required')).toBeInTheDocument()
    expect(mockOnSave).not.toHaveBeenCalled()
  })

  it('calls onSave with correct data', async () => {
    mockOnSave.mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<ScheduleEditor taskId={1} onSave={mockOnSave} />)

    await user.type(screen.getByPlaceholderText(/0 2 \* \* \*/), '0 2 * * *')
    await user.click(screen.getByText('Create Schedule'))

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        cron_expression: '0 2 * * *',
        is_active: true,
      })
    })
  })

  it('shows delete button in edit mode', () => {
    const schedule = {
      id: 1, task_id: 1, cron_expression: '0 2 * * *', is_active: true, created_at: new Date().toISOString(),
    }
    render(<ScheduleEditor taskId={1} schedule={schedule} isEditing onSave={mockOnSave} onDelete={mockOnDelete} />)
    expect(screen.getByText('Update Schedule')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('shows confirm delete after clicking delete', async () => {
    const user = userEvent.setup()
    const schedule = {
      id: 1, task_id: 1, cron_expression: '0 2 * * *', is_active: true, created_at: new Date().toISOString(),
    }
    render(<ScheduleEditor taskId={1} schedule={schedule} isEditing onSave={mockOnSave} onDelete={mockOnDelete} />)

    await user.click(screen.getByText('Delete'))
    expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
  })

  it('calls onDelete when confirmed', async () => {
    mockOnDelete.mockResolvedValue(undefined)
    const user = userEvent.setup()
    const schedule = {
      id: 1, task_id: 1, cron_expression: '0 2 * * *', is_active: true, created_at: new Date().toISOString(),
    }
    render(<ScheduleEditor taskId={1} schedule={schedule} isEditing onSave={mockOnSave} onDelete={mockOnDelete} />)

    await user.click(screen.getByText('Delete'))
    await user.click(screen.getByText('Confirm Delete'))

    await waitFor(() => {
      expect(mockOnDelete).toHaveBeenCalled()
    })
  })

  it('disables save button when loading', () => {
    render(<ScheduleEditor taskId={1} onSave={mockOnSave} isLoading />)
    expect(screen.getByText('Create Schedule')).toBeDisabled()
  })

  it('shows crontab.guru link', () => {
    render(<ScheduleEditor taskId={1} onSave={mockOnSave} />)
    expect(screen.getByText('crontab.guru')).toBeInTheDocument()
  })
})
