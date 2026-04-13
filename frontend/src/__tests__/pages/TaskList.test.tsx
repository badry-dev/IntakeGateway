import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { TaskList } from '@/pages/TaskList'

vi.mock('@/hooks/api', () => ({
  useTasks: vi.fn(),
  useTriggerRun: vi.fn(),
  useDeleteTask: vi.fn(),
  useListSchedules: vi.fn(),
}))

import { useTasks, useTriggerRun, useDeleteTask, useListSchedules } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

const mockMutations = () => {
  vi.mocked(useTriggerRun).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
  vi.mocked(useDeleteTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
  vi.mocked(useListSchedules).mockReturnValue({ data: { schedules: [], total_count: 0 }, isLoading: false } as any)
}

describe('TaskList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockMutations()
  })

  it('should render tasks heading', () => {
    vi.mocked(useTasks).mockReturnValue({ data: [], isLoading: false, error: null } as any)
    render(<TaskList />, { wrapper: createWrapper() })
    expect(screen.getByText('Tasks')).toBeInTheDocument()
  })

  it('should show New Task button', () => {
    vi.mocked(useTasks).mockReturnValue({ data: [], isLoading: false, error: null } as any)
    render(<TaskList />, { wrapper: createWrapper() })
    expect(screen.getByText('New Task').closest('a')).toHaveAttribute('href', '/tasks/new')
  })

  it('should display empty state when no tasks', async () => {
    vi.mocked(useTasks).mockReturnValue({ data: [], isLoading: false, error: null } as any)
    render(<TaskList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Create Your First Task')).toBeInTheDocument()
    })
  })

  it('should display task cards when data loads', async () => {
    vi.mocked(useTasks).mockReturnValue({
      data: [
        { id: 1, name: 'Sync Users', description: 'Import users', http_method: 'GET', endpoint_path: 'https://api.example.com/users', dest_table: 'USERS', is_active: true, batch_size: 500, upsert_enabled: false, continue_on_error: false, auth_type: 'none' },
      ],
      isLoading: false,
      error: null,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Sync Users')).toBeInTheDocument()
      expect(screen.getByText('Import users')).toBeInTheDocument()
    })
  })

  it('should display action buttons for tasks', async () => {
    vi.mocked(useTasks).mockReturnValue({
      data: [
        { id: 1, name: 'Test Task', http_method: 'GET', endpoint_path: 'https://api.test.com', dest_table: 'TEST', is_active: true, batch_size: 500, upsert_enabled: false, continue_on_error: false, auth_type: 'none' },
      ],
      isLoading: false,
      error: null,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Run')).toBeInTheDocument()
      expect(screen.getByText('Edit')).toBeInTheDocument()
      expect(screen.getByText('Delete')).toBeInTheDocument()
    })
  })

  it('should handle API errors', () => {
    vi.mocked(useTasks).mockReturnValue({ data: undefined, isLoading: false, error: new Error('Failed to load') } as any)
    render(<TaskList />, { wrapper: createWrapper() })
    expect(screen.getByText(/Error loading tasks/)).toBeInTheDocument()
  })
})
