import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Dashboard } from '@/pages/Dashboard'

// Mock the API hooks
vi.mock('@/hooks/api', () => ({
  useTaskStats: vi.fn(),
  useRecentRuns: vi.fn(),
}))

import { useTaskStats, useRecentRuns } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render dashboard heading', () => {
    vi.mocked(useTaskStats).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any)
    
    vi.mocked(useRecentRuns).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Dashboard/i)).toBeInTheDocument()
  })

  it('should display loading state initially', () => {
    vi.mocked(useTaskStats).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)
    
    vi.mocked(useRecentRuns).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('should display stat cards when data loads', async () => {
    vi.mocked(useTaskStats).mockReturnValue({
      data: {
        total_runs: 100,
        successful_runs: 80,
        failed_runs: 20,
        success_rate: 0.8,
        avg_duration_ms: 1500,
        total_records: 5000,
      },
      isLoading: false,
      error: null,
    } as any)
    
    vi.mocked(useRecentRuns).mockReturnValue({
      data: {
        results: [],
        total: 0,
      },
      isLoading: false,
      error: null,
    } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/100/)).toBeInTheDocument()
      expect(screen.getByText(/80/)).toBeInTheDocument()
      expect(screen.getByText(/20/)).toBeInTheDocument()
    })
  })

  it('should display recent runs list', async () => {
    vi.mocked(useTaskStats).mockReturnValue({
      data: {
        total_runs: 10,
        successful_runs: 8,
        failed_runs: 2,
        success_rate: 0.8,
        avg_duration_ms: 1500,
        total_records: 500,
      },
      isLoading: false,
      error: null,
    } as any)
    
    vi.mocked(useRecentRuns).mockReturnValue({
      data: {
        results: [
          {
            id: '1',
            task_id: 'task-1',
            status: 'SUCCESS',
            records_inserted: 100,
            records_updated: 50,
            records_failed: 0,
            execution_time_ms: 2000,
            started_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/Run #1/)).toBeInTheDocument()
    })
  })

  it('should handle error state gracefully', () => {
    vi.mocked(useTaskStats).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch stats'),
    } as any)
    
    vi.mocked(useRecentRuns).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument()
  })

  it('should have link to New Task button', () => {
    vi.mocked(useTaskStats).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any)
    
    vi.mocked(useRecentRuns).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any)

    render(<Dashboard />, { wrapper: createWrapper() })
    
    expect(screen.getByRole('link', { name: /New Task/i })).toHaveAttribute('href', '/tasks/new')
  })
})
