import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ScheduleEditor } from '@/components/ScheduleEditor'

describe('ScheduleEditor', () => {
  const mockOnSave = vi.fn()
  const mockOnDelete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders form with cron input field', () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    expect(screen.getByPlaceholderText(/0 2 \* \* \*/)).toBeInTheDocument()
    expect(screen.getByText('Create Schedule')).toBeInTheDocument()
  })

  it('shows error for invalid cron expression', async () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const input = screen.getByPlaceholderText(/0 2 \* \* \*/)
    await userEvent.type(input, 'invalid cron')
    
    await waitFor(() => {
      expect(screen.getByText('Invalid cron expression')).toBeInTheDocument()
    })
  })

  it('validates required cron expression', async () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const saveButton = screen.getByText('Create Schedule')
    await userEvent.click(saveButton)
    
    expect(screen.getByText('Cron expression is required')).toBeInTheDocument()
    expect(mockOnSave).not.toHaveBeenCalled()
  })

  it('populates cron from preset selection', async () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const presetSelect = screen.getByDisplayValue('Select a preset...')
    await userEvent.click(presetSelect)
    
    const dailyOption = screen.getByText('Daily at 2:00 AM')
    await userEvent.click(dailyOption)
    
    const input = screen.getByPlaceholderText(/0 2 \* \* \*/) as HTMLInputElement
    expect(input.value).toBe('0 2 * * *')
  })

  it('shows next run date when valid cron is entered', async () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const input = screen.getByPlaceholderText(/0 2 \* \* \*/)
    await userEvent.clear(input)
    await userEvent.type(input, '0 2 * * *')
    
    await waitFor(() => {
      expect(screen.getByText('Next Run')).toBeInTheDocument()
    })
  })

  it('calls onSave with correct data when form submitted', async () => {
    mockOnSave.mockResolvedValue(undefined)
    
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const input = screen.getByPlaceholderText(/0 2 \* \* \*/)
    await userEvent.type(input, '0 2 * * *')
    
    const saveButton = screen.getByText('Create Schedule')
    await userEvent.click(saveButton)
    
    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        cron_expression: '0 2 * * *',
        is_active: true,
      })
    })
  })

  it('toggles active checkbox', async () => {
    mockOnSave.mockResolvedValue(undefined)
    
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const input = screen.getByPlaceholderText(/0 2 \* \* \*/)
    await userEvent.type(input, '0 2 * * *')
    
    const activeCheckbox = screen.getByRole('checkbox')
    await userEvent.click(activeCheckbox)
    
    const saveButton = screen.getByText('Create Schedule')
    await userEvent.click(saveButton)
    
    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        cron_expression: '0 2 * * *',
        is_active: false,
      })
    })
  })

  it('shows delete button and confirmation in edit mode', async () => {
    const schedule = {
      id: 1,
      task_id: 1,
      cron_expression: '0 2 * * *',
      is_active: true,
      created_at: new Date().toISOString(),
    }
    
    render(
      <ScheduleEditor 
        taskId={1}
        schedule={schedule}
        isEditing={true}
        onSave={mockOnSave}
        onDelete={mockOnDelete}
      />
    )
    
    expect(screen.getByText('Update Schedule')).toBeInTheDocument()
    const deleteButton = screen.getByText('Delete')
    expect(deleteButton).toBeInTheDocument()
  })

  it('shows confirm delete button after clicking delete', async () => {
    const schedule = {
      id: 1,
      task_id: 1,
      cron_expression: '0 2 * * *',
      is_active: true,
      created_at: new Date().toISOString(),
    }
    
    render(
      <ScheduleEditor 
        taskId={1}
        schedule={schedule}
        isEditing={true}
        onSave={mockOnSave}
        onDelete={mockOnDelete}
      />
    )
    
    const deleteButton = screen.getByText('Delete')
    await userEvent.click(deleteButton)
    
    expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('calls onDelete when confirm delete is clicked', async () => {
    mockOnDelete.mockResolvedValue(undefined)
    
    const schedule = {
      id: 1,
      task_id: 1,
      cron_expression: '0 2 * * *',
      is_active: true,
      created_at: new Date().toISOString(),
    }
    
    render(
      <ScheduleEditor 
        taskId={1}
        schedule={schedule}
        isEditing={true}
        onSave={mockOnSave}
        onDelete={mockOnDelete}
      />
    )
    
    const deleteButton = screen.getByText('Delete')
    await userEvent.click(deleteButton)
    
    const confirmButton = screen.getByText('Confirm Delete')
    await userEvent.click(confirmButton)
    
    await waitFor(() => {
      expect(mockOnDelete).toHaveBeenCalled()
    })
  })

  it('disables save button when loading', () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
        isLoading={true}
      />
    )
    
    const saveButton = screen.getByText('Create Schedule')
    expect(saveButton).toBeDisabled()
  })

  it('displays all preset options', async () => {
    render(
      <ScheduleEditor 
        taskId={1}
        onSave={mockOnSave}
      />
    )
    
    const presetSelect = screen.getByDisplayValue('Select a preset...')
    await userEvent.click(presetSelect)
    
    expect(screen.getByText('Every Hour')).toBeInTheDocument()
    expect(screen.getByText('Daily at 2:00 AM')).toBeInTheDocument()
    expect(screen.getByText('Daily at 12:00 PM')).toBeInTheDocument()
    expect(screen.getByText('Weekly (Sunday at 2:00 AM)')).toBeInTheDocument()
    expect(screen.getByText('Monthly (1st at 2:00 AM)')).toBeInTheDocument()
  })
})
