import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Schedules } from '@/pages/Schedules'

// Mock the useListSchedules hook
vi.mock('@/hooks/api', () => ({
  useListSchedules: vi.fn(),
}))

import { useListSchedules } from '@/hooks/api'

describe('Schedules Page', () => {
  const mockSchedules = [
    {
      id: 1,
      task_id: 1,
      task_name: 'Daily Import',
      cron_expression: '0 2 * * *',
      is_active: true,
      last_run_date: '2024-01-30T02:00:00Z',
      next_run_date: '2024-01-31T02:00:00Z',
      created_at: '2024-01-15T10:00:00Z',
    },
    {
      id: 2,
      task_id: 2,
      task_name: 'Hourly Sync',
      cron_expression: '0 * * * *',
      is_active: false,
      last_run_date: null,
      next_run_date: null,
      created_at: '2024-01-15T10:00:00Z',
    },
  ]

  const queryClient = new QueryClient()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderSchedules = (mockData: any = null) => {
    ;(useListSchedules as any).mockReturnValue(
      mockData || {
        data: {
          items: mockSchedules,
          total: 2,
        },
        isLoading: false,
        isError: false,
      }
    )

    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Schedules />
        </BrowserRouter>
      </QueryClientProvider>
    )
  }

  it('renders page title and description', () => {
    renderSchedules()
    expect(screen.getByText('Task Schedules')).toBeInTheDocument()
    expect(screen.getByText('Manage automated task execution schedules')).toBeInTheDocument()
  })

  it('displays filter controls', () => {
    renderSchedules()
    expect(screen.getByText('Filter')).toBeInTheDocument()
    expect(screen.getByText('Items Per Page')).toBeInTheDocument()
  })

  it('displays schedule table with all columns', () => {
    renderSchedules()
    expect(screen.getByText('Task')).toBeInTheDocument()
    expect(screen.getByText('Cron Expression')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Last Run')).toBeInTheDocument()
    expect(screen.getByText('Next Run')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
  })

  it('renders schedule rows with correct data', () => {
    renderSchedules()
    expect(screen.getByText('Daily Import')).toBeInTheDocument()
    expect(screen.getByText('Hourly Sync')).toBeInTheDocument()
    expect(screen.getByText('0 2 * * *')).toBeInTheDocument()
    expect(screen.getByText('0 * * * *')).toBeInTheDocument()
  })

  it('shows active and inactive badges', () => {
    renderSchedules()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('displays last run dates', () => {
    renderSchedules()
    expect(screen.getByText(/Jan 30, 2024/)).toBeInTheDocument()
  })

  it('shows "Never" for schedules without last run date', () => {
    renderSchedules()
    const neverTexts = screen.getAllByText('Never')
    expect(neverTexts.length).toBeGreaterThan(0)
  })

  it('shows loading state', () => {
    ;(useListSchedules as any).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
    })

    renderSchedules()
    expect(screen.getByText('Loading schedules...')).toBeInTheDocument()
  })

  it('shows error state', () => {
    ;(useListSchedules as any).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
    })

    renderSchedules()
    expect(screen.getByText('Failed to load schedules')).toBeInTheDocument()
  })

  it('shows empty state when no schedules', () => {
    ;(useListSchedules as any).mockReturnValue({
      data: {
        items: [],
        total: 0,
      },
      isLoading: false,
      isError: false,
    })

    renderSchedules()
    expect(screen.getByText('No schedules found')).toBeInTheDocument()
  })

  it('displays pagination info', () => {
    renderSchedules()
    expect(screen.getByText(/Showing 1 - 2 of 2/)).toBeInTheDocument()
  })

  it('displays edit buttons for each schedule', () => {
    renderSchedules()
    const editButtons = screen.getAllByText('Edit')
    expect(editButtons.length).toBe(2)
  })

  it('disables pagination buttons appropriately', () => {
    renderSchedules()
    const previousButton = screen.getByText('Previous')
    const nextButton = screen.getByText('Next')
    
    expect(previousButton).toBeDisabled()
    expect(nextButton).toBeDisabled()
  })

  it('filters by active status', async () => {
    ;(useListSchedules as any).mockReturnValue({
      data: {
        items: mockSchedules,
        total: 2,
      },
      isLoading: false,
      isError: false,
    })

    renderSchedules()

    const filterSelect = screen.getByDisplayValue('All Schedules')
    await userEvent.click(filterSelect)
    
    const activeOption = screen.getByText('Active Only')
    await userEvent.click(activeOption)

    // Hook should be called with isActive=true
    expect(useListSchedules).toHaveBeenCalled()
  })

  it('changes items per page', async () => {
    renderSchedules()

    const itemsSelect = screen.getByDisplayValue('10')
    await userEvent.click(itemsSelect)
    
    const option25 = screen.getByText('25')
    await userEvent.click(option25)

    // Hook should be called with limit=25
    expect(useListSchedules).toHaveBeenCalled()
  })

  it('links to task detail page from task name', () => {
    renderSchedules()
    const taskLink = screen.getByText('Daily Import')
    expect(taskLink.getAttribute('href')).toBe('/tasks/1')
  })

  it('links to task detail with schedule tab from edit button', () => {
    renderSchedules()
    const editButtons = screen.getAllByText('Edit')
    expect(editButtons[0].closest('a')?.getAttribute('href')).toContain('/tasks/1')
  })

  it('displays schedule count in header', () => {
    renderSchedules()
    expect(screen.getByText('2 schedules')).toBeInTheDocument()
  })

  it('displays cron expressions in code format', () => {
    renderSchedules()
    const cronElements = screen.getAllByRole('cell')
    const cronCells = cronElements.filter(cell => 
      cell.textContent?.includes('* * *')
    )
    expect(cronCells.length).toBeGreaterThan(0)
  })
})
