import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { RunsList } from '@/pages/RunsList'

vi.mock('@/hooks/api', () => ({
  useRecentRuns: vi.fn(),
}))

import { useRecentRuns } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('RunsList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render page heading', () => {
    vi.mocked(useRecentRuns).mockReturnValue({ data: [], isLoading: false, error: null } as any)
    render(<RunsList />, { wrapper: createWrapper() })
    expect(screen.getByText('Task Runs')).toBeInTheDocument()
  })

  it('should display empty state when no runs', async () => {
    vi.mocked(useRecentRuns).mockReturnValue({ data: [], isLoading: false, error: null } as any)
    render(<RunsList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('No runs yet')).toBeInTheDocument()
    })
  })

  it('should display runs in a table', async () => {
    vi.mocked(useRecentRuns).mockReturnValue({
      data: [
        { id: 1, task_id: 1, task_name: 'Sync Users', status: 'SUCCESS', rows_fetched: 50, rows_inserted: 50, error_count: 0, started_at: new Date().toISOString() },
      ],
      isLoading: false,
      error: null,
    } as any)

    render(<RunsList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Sync Users')).toBeInTheDocument()
      expect(screen.getByText('SUCCESS')).toBeInTheDocument()
    })
  })

  it('should handle API errors', () => {
    vi.mocked(useRecentRuns).mockReturnValue({ data: undefined, isLoading: false, error: new Error('Failed') } as any)
    render(<RunsList />, { wrapper: createWrapper() })
    expect(screen.getByText(/Error loading runs/)).toBeInTheDocument()
  })
})
