import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { TaskDetail } from '@/pages/TaskDetail'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn().mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false }),
  useBackfillTask: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useTask: vi.fn(),
  useUpdateTask: vi.fn(),
  useDeleteTask: vi.fn(),
  useColumnMappings: vi.fn(),
  useSchedule: vi.fn(),
  useCreateSchedule: vi.fn(),
  useUpdateSchedule: vi.fn(),
  useDeleteSchedule: vi.fn(),
}))

vi.mock('@/components/ColumnMappingEditor', () => ({
  ColumnMappingEditor: () => <div data-testid="column-mapping-editor">ColumnMappingEditor</div>,
}))

vi.mock('@/components/ScheduleEditor', () => ({
  ScheduleEditor: () => <div data-testid="schedule-editor">ScheduleEditor</div>,
}))

import { useTask, useUpdateTask, useDeleteTask, useColumnMappings, useSchedule, useCreateSchedule, useUpdateSchedule, useDeleteSchedule } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/tasks/:id" element={children} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

const mockTask = {
  id: 1, name: 'Sync Users', description: 'Import user data', http_method: 'GET',
  endpoint_path: 'https://api.example.com/users', dest_table: 'USERS', batch_size: 500,
  is_active: true, auth_type: 'none', upsert_enabled: false, continue_on_error: false,
  headers_json: {}, body_json: {}, created_at: new Date().toISOString(),
}

describe('TaskDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useUpdateTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useDeleteTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useColumnMappings).mockReturnValue({ data: [], isLoading: false } as any)
    vi.mocked(useSchedule).mockReturnValue({ data: null, refetch: vi.fn() } as any)
    vi.mocked(useCreateSchedule).mockReturnValue({ mutateAsync: vi.fn() } as any)
    vi.mocked(useUpdateSchedule).mockReturnValue({ mutateAsync: vi.fn() } as any)
    vi.mocked(useDeleteSchedule).mockReturnValue({ mutateAsync: vi.fn() } as any)
    window.history.pushState({}, '', '/tasks/1')
  })

  it('should show loading state', () => {
    vi.mocked(useTask).mockReturnValue({ data: undefined, isLoading: true, error: null } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText('Back to Tasks')).toBeInTheDocument()
  })

  it('should show error state', () => {
    vi.mocked(useTask).mockReturnValue({ data: undefined, isLoading: false, error: new Error('Not found') } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText(/Error loading task/)).toBeInTheDocument()
  })

  it('should display task details', async () => {
    vi.mocked(useTask).mockReturnValue({ data: mockTask, isLoading: false, error: null } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Sync Users')).toBeInTheDocument()
      expect(screen.getByText('GET')).toBeInTheDocument()
      expect(screen.getByText('USERS')).toBeInTheDocument()
    })
  })

  it('should show Edit and Delete buttons', () => {
    vi.mocked(useTask).mockReturnValue({ data: mockTask, isLoading: false, error: null } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText('Edit')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('should show tabs for Details, Schedule, Mappings', () => {
    vi.mocked(useTask).mockReturnValue({ data: mockTask, isLoading: false, error: null } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText('Task Details')).toBeInTheDocument()
    expect(screen.getByText(/Schedule/)).toBeInTheDocument()
    expect(screen.getByText(/Column Mappings/)).toBeInTheDocument()
  })
})
