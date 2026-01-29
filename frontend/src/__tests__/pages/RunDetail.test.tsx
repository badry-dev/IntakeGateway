import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { RunDetail } from '@/pages/RunDetail'

vi.mock('@/hooks/api', () => ({
  useRun: vi.fn(),
}))

import { useRun } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/runs/:id" element={children} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('RunDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render run detail heading', () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        id: 'run-1',
        task_id: 'task-1',
        status: 'completed',
        total_records: 100,
        successful_records: 100,
        failed_records: 0,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        logs: [],
        errors: [],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Run Details/i)).toBeInTheDocument()
  })

  it('should display loading state', () => {
    vi.mocked(useRun).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('should display run status and timing', async () => {
    const startTime = new Date('2024-01-15T10:00:00Z')
    const endTime = new Date('2024-01-15T10:05:00Z')

    vi.mocked(useRun).mockReturnValue({
      data: {
        id: 'run-1',
        task_id: 'task-1',
        status: 'completed',
        total_records: 100,
        successful_records: 100,
        failed_records: 0,
        started_at: startTime.toISOString(),
        completed_at: endTime.toISOString(),
        logs: [],
        errors: [],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/completed/i)).toBeInTheDocument()
    })
  })

  it('should display record statistics', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        id: 'run-1',
        task_id: 'task-1',
        status: 'completed',
        total_records: 100,
        successful_records: 95,
        failed_records: 5,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        logs: [],
        errors: [],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/100/)).toBeInTheDocument()
      expect(screen.getByText(/95/)).toBeInTheDocument()
    })
  })

  it('should display logs section', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        id: 'run-1',
        task_id: 'task-1',
        status: 'completed',
        total_records: 100,
        successful_records: 100,
        failed_records: 0,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        logs: [
          { timestamp: new Date().toISOString(), message: 'Run started' },
          { timestamp: new Date().toISOString(), message: 'Processing records' },
        ],
        errors: [],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/Logs/i)).toBeInTheDocument()
    })
  })

  it('should display errors table when present', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        id: 'run-1',
        task_id: 'task-1',
        status: 'partial_failure',
        total_records: 100,
        successful_records: 95,
        failed_records: 5,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        logs: [],
        errors: [
          {
            row_number: 1,
            error_message: 'Invalid email format',
            record_data: '{"email": "invalid"}',
          },
        ],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/Errors/i)).toBeInTheDocument()
    })
  })

  it('should link to task details', async () => {
    vi.mocked(useRun).mockReturnValue({
      data: {
        id: 'run-1',
        task_id: 'task-1',
        status: 'completed',
        total_records: 100,
        successful_records: 100,
        failed_records: 0,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        logs: [],
        errors: [],
      },
      isLoading: false,
      error: null,
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      const taskLink = screen.getByRole('link', { name: /View Task/i })
      expect(taskLink).toHaveAttribute('href', '/tasks/task-1')
    })
  })

  it('should handle error state', () => {
    vi.mocked(useRun).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Run not found'),
    } as any)

    render(<RunDetail />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument()
  })
})
