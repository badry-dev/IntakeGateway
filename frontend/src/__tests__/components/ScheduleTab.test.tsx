import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import TaskDetail from '@/pages/TaskDetail'

// Mock the API hooks
vi.mock('@/hooks/api', () => ({
  useTask: () => ({
    data: {
      id: 1,
      name: 'Test Task',
      description: 'Test Description',
      endpoint_path: 'https://api.example.com/users',
      http_method: 'GET',
      dest_table: 'USERS',
      headers_json: {},
      body_json: {},
      batch_size: 500,
      is_active: true,
      created_at: '2025-01-30T10:00:00Z',
    },
    isLoading: false,
    error: null,
  }),
  useUpdateTask: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteTask: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useColumnMappings: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
  useSchedule: () => ({
    data: {
      id: 1,
      task_id: 1,
      cron_expression: '0 2 * * *',
      is_active: true,
      last_run_date: '2025-01-30T02:00:00Z',
      next_run_date: '2025-01-31T02:00:00Z',
      created_at: '2025-01-30T10:00:00Z',
    },
    isLoading: false,
  }),
}))

// Mock ScheduleEditor component
vi.mock('@/components/ScheduleEditor', () => ({
  ScheduleEditor: ({ taskId, existingSchedule }: any) => (
    <div data-testid="schedule-editor">
      Schedule Editor - Task {taskId}
      {existingSchedule && <p>Existing: {existingSchedule.cron_expression}</p>}
    </div>
  ),
}))

// Mock ColumnMappingEditor component
vi.mock('@/components/ColumnMappingEditor', () => ({
  ColumnMappingEditor: ({ taskId }: any) => (
    <div data-testid="column-mapping-editor">Column Mapping Editor - Task {taskId}</div>
  ),
}))

const queryClient = new QueryClient()

function renderWithRouter(component: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('TaskDetail - Schedule Tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render task detail with Schedule tab', () => {
    renderWithRouter(<TaskDetail />)
    
    expect(screen.getByText('Task Details')).toBeInTheDocument()
    expect(screen.getByText('Schedule')).toBeInTheDocument()
    expect(screen.getByText('Column Mappings')).toBeInTheDocument()
  })

  it('should display Active badge when schedule exists', () => {
    renderWithRouter(<TaskDetail />)
    
    const scheduleTab = screen.getByText('Schedule')
    expect(scheduleTab.closest('button')).toBeInTheDocument()
    
    // Should show Active badge
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('should navigate to Schedule tab when clicked', async () => {
    renderWithRouter(<TaskDetail />)
    
    const scheduleTab = screen.getByRole('button', { name: /Schedule/i })
    fireEvent.click(scheduleTab)
    
    // Schedule editor should be visible
    expect(screen.getByTestId('schedule-editor')).toBeInTheDocument()
  })

  it('should show schedule details in Schedule tab', async () => {
    renderWithRouter(<TaskDetail />)
    
    const scheduleTab = screen.getByRole('button', { name: /Schedule/i })
    fireEvent.click(scheduleTab)
    
    // Should show configured schedule info
    expect(screen.getByText(/Schedule configured/i)).toBeInTheDocument()
    expect(screen.getByText(/0 2 \* \* \*/)).toBeInTheDocument()
  })

  it('should render ScheduleEditor component in Schedule tab', async () => {
    renderWithRouter(<TaskDetail />)
    
    const scheduleTab = screen.getByRole('button', { name: /Schedule/i })
    fireEvent.click(scheduleTab)
    
    expect(screen.getByTestId('schedule-editor')).toBeInTheDocument()
  })

  it('should show Task Details tab by default', () => {
    renderWithRouter(<TaskDetail />)
    
    // Details tab should be active
    expect(screen.getByText('Test Task')).toBeInTheDocument()
  })

  it('should maintain tab state when switching tabs', async () => {
    renderWithRouter(<TaskDetail />)
    
    // Switch to Schedule tab
    const scheduleTab = screen.getByRole('button', { name: /Schedule/i })
    fireEvent.click(scheduleTab)
    expect(screen.getByTestId('schedule-editor')).toBeInTheDocument()
    
    // Switch to Details tab
    const detailsTab = screen.getByRole('button', { name: /Task Details/i })
    fireEvent.click(detailsTab)
    expect(screen.getByText('Test Task')).toBeInTheDocument()
    
    // Switch back to Schedule tab
    fireEvent.click(scheduleTab)
    expect(screen.getByTestId('schedule-editor')).toBeInTheDocument()
  })
})
