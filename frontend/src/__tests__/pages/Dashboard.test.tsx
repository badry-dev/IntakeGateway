import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Dashboard } from '@/pages/Dashboard'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn().mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false }),
  useRecentRuns: vi.fn(),
  useTasks: vi.fn(),
}))

import { useRecentRuns, useTasks } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render dashboard heading', () => {
    vi.mocked(useRecentRuns).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)
    vi.mocked(useTasks).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('should display stat cards with data', async () => {
    vi.mocked(useRecentRuns).mockReturnValue({
      data: [
        { id: 1, task_id: 1, status: 'SUCCESS', rows_fetched: 10, rows_inserted: 10, error_count: 0, started_at: new Date().toISOString() },
        { id: 2, task_id: 1, status: 'FAILED', rows_fetched: 5, rows_inserted: 0, error_count: 5, started_at: new Date().toISOString() },
      ],
      isLoading: false,
      error: null,
    } as any)
    vi.mocked(useTasks).mockReturnValue({ data: [{ id: 1 }, { id: 2 }], isLoading: false, error: null } as any)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Succeeded')).toBeInTheDocument()
      expect(screen.getByText('Failed')).toBeInTheDocument()
      expect(screen.getByText('Total Tasks')).toBeInTheDocument()
    })
  })

  it('should display recent runs table', async () => {
    vi.mocked(useRecentRuns).mockReturnValue({
      data: [
        { id: 1, task_id: 1, task_name: 'Sync Users', status: 'SUCCESS', rows_fetched: 100, rows_inserted: 100, error_count: 0, started_at: new Date().toISOString() },
      ],
      isLoading: false,
      error: null,
    } as any)
    vi.mocked(useTasks).mockReturnValue({ data: [], isLoading: false, error: null } as any)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Recent Runs')).toBeInTheDocument()
      expect(screen.getByText('Sync Users')).toBeInTheDocument()
      expect(screen.getByText('SUCCESS')).toBeInTheDocument()
    })
  })

  it('should have New Task button linking to /tasks/new', () => {
    vi.mocked(useRecentRuns).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)
    vi.mocked(useTasks).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    expect(screen.getByText('New Task').closest('a')).toHaveAttribute('href', '/tasks/new')
  })

  it('should show quick actions', () => {
    vi.mocked(useRecentRuns).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)
    vi.mocked(useTasks).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    expect(screen.getByText('Quick Actions')).toBeInTheDocument()
    expect(screen.getByText('View All Tasks')).toBeInTheDocument()
    expect(screen.getByText('View All Runs')).toBeInTheDocument()
  })
})
