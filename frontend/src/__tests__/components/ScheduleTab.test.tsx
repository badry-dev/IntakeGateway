import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { TaskDetail } from '@/pages/TaskDetail'

vi.mock('@/hooks/api', () => ({
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
  id: 1, name: 'Sync Users', description: 'Import data', http_method: 'GET',
  endpoint_path: 'https://api.example.com/users', dest_table: 'USERS', batch_size: 500,
  is_active: true, auth_type: 'none', upsert_enabled: false, continue_on_error: false,
  headers_json: {}, body_json: {}, created_at: new Date().toISOString(),
}

describe('TaskDetail Schedule Tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useUpdateTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useDeleteTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useColumnMappings).mockReturnValue({ data: [], isLoading: false } as any)
    vi.mocked(useCreateSchedule).mockReturnValue({ mutateAsync: vi.fn() } as any)
    vi.mocked(useUpdateSchedule).mockReturnValue({ mutateAsync: vi.fn() } as any)
    vi.mocked(useDeleteSchedule).mockReturnValue({ mutateAsync: vi.fn() } as any)
    window.history.pushState({}, '', '/tasks/1')
  })

  it('should show Schedule tab', () => {
    vi.mocked(useTask).mockReturnValue({ data: mockTask, isLoading: false, error: null } as any)
    vi.mocked(useSchedule).mockReturnValue({ data: null, refetch: vi.fn() } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText(/Schedule/)).toBeInTheDocument()
  })

  it('should show Active tag when schedule exists', () => {
    vi.mocked(useTask).mockReturnValue({ data: mockTask, isLoading: false, error: null } as any)
    vi.mocked(useSchedule).mockReturnValue({
      data: { id: 1, task_id: 1, cron_expression: '0 2 * * *', is_active: true, created_at: new Date().toISOString() },
      refetch: vi.fn(),
    } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('should show all three tabs', () => {
    vi.mocked(useTask).mockReturnValue({ data: mockTask, isLoading: false, error: null } as any)
    vi.mocked(useSchedule).mockReturnValue({ data: null, refetch: vi.fn() } as any)
    render(<TaskDetail />, { wrapper: createWrapper() })
    expect(screen.getByText('Task Details')).toBeInTheDocument()
    expect(screen.getByText(/Schedule/)).toBeInTheDocument()
    expect(screen.getByText(/Column Mappings/)).toBeInTheDocument()
  })
})
