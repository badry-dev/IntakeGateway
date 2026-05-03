import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { RunDetail } from '@/pages/RunDetail'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn().mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false }),
  useBackfillTask: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useRun: vi.fn(),
}))

import { useRun } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/runs/:id" element={children} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

const mockRun = {
  id: 1, task_id: 1, task_name: 'Sync Users', status: 'SUCCESS',
  rows_fetched: 100, rows_inserted: 95, error_count: 0,
  started_at: new Date().toISOString(), ended_at: new Date().toISOString(),
  execution_logs: [{ id: 1, task_id: 1, run_id: 1, step_name: 'FETCH', status: 'OK', message: 'Fetched 100 records', created_at: new Date().toISOString() }],
  row_errors: [],
}

describe('RunDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.pushState({}, '', '/runs/1')
  })

  it('should show loading state', () => {
    vi.mocked(useRun).mockReturnValue({ data: undefined, isLoading: true, error: null } as any)
    render(<RunDetail />, { wrapper: createWrapper() })
    expect(screen.getByText('Back to Runs')).toBeInTheDocument()
  })

  it('should show error state', () => {
    vi.mocked(useRun).mockReturnValue({ data: undefined, isLoading: false, error: new Error('Not found') } as any)
    render(<RunDetail />, { wrapper: createWrapper() })
    expect(screen.getByText(/Error loading run/)).toBeInTheDocument()
  })

  it('should display run details', async () => {
    vi.mocked(useRun).mockReturnValue({ data: mockRun, isLoading: false, error: null } as any)
    render(<RunDetail />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Run #1')).toBeInTheDocument()
      expect(screen.getByText('SUCCESS')).toBeInTheDocument()
      expect(screen.getByText(/Sync Users/)).toBeInTheDocument()
    })
  })

  it('should display execution statistics', async () => {
    vi.mocked(useRun).mockReturnValue({ data: mockRun, isLoading: false, error: null } as any)
    render(<RunDetail />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Inserted')).toBeInTheDocument()
      expect(screen.getByText('Errors')).toBeInTheDocument()
    })
  })

  it('should display execution logs', async () => {
    vi.mocked(useRun).mockReturnValue({ data: mockRun, isLoading: false, error: null } as any)
    render(<RunDetail />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText(/Execution Logs/)).toBeInTheDocument()
      expect(screen.getByText('Fetched 100 records')).toBeInTheDocument()
    })
  })

  it('should show success result when no errors', async () => {
    vi.mocked(useRun).mockReturnValue({ data: mockRun, isLoading: false, error: null } as any)
    render(<RunDetail />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Run completed successfully')).toBeInTheDocument()
    })
  })
})
