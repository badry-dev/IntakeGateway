import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { RunsList } from '@/pages/RunsList'

vi.mock('@/hooks/api', () => ({
  useRuns: vi.fn(),
}))

import { useRun } from '@/hooks/api'

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

describe('RunsList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render runs page heading', () => {
    vi.mocked(useRun).mockReturnValue({
      data: { results: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Runs/)).toBeInTheDocument()
  })

  it('should display loading state', () => {
    vi.mocked(useRun).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('should display empty state when no runs', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: { results: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/No runs yet/i)).toBeInTheDocument()
    })
  })

  it('should display run cards when data loads', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        results: [
          {
            id: 'run-1',
            task_id: 'task-1',
            status: 'completed',
            total_records: 100,
            successful_records: 100,
            failed_records: 0,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/run-1/)).toBeInTheDocument()
      expect(screen.getByText(/completed/i)).toBeInTheDocument()
    })
  })

  it('should show run status badges', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        results: [
          {
            id: 'run-1',
            task_id: 'task-1',
            status: 'running',
            total_records: 100,
            successful_records: 50,
            failed_records: 0,
            started_at: new Date().toISOString(),
            completed_at: null,
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/running/i)).toBeInTheDocument()
    })
  })

  it('should display record counts', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        results: [
          {
            id: 'run-1',
            task_id: 'task-1',
            status: 'completed',
            total_records: 100,
            successful_records: 95,
            failed_records: 5,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/100/)).toBeInTheDocument()
      expect(screen.getByText(/95/)).toBeInTheDocument()
    })
  })

  it('should link to run details', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        results: [
          {
            id: 'run-1',
            task_id: 'task-1',
            status: 'completed',
            total_records: 100,
            successful_records: 100,
            failed_records: 0,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /run-1/i })
      expect(link).toHaveAttribute('href', '/runs/run-1')
    })
  })

  it('should handle API errors', () => {
    vi.mocked(useRun).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load runs'),
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument()
  })
})
