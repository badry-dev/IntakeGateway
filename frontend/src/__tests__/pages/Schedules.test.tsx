import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Schedules } from '@/pages/Schedules'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn().mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false }),
  useListSchedules: vi.fn(),
  useTasks: vi.fn(),
}))

import { useListSchedules, useTasks } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Schedules', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useTasks).mockReturnValue({ data: [], isLoading: false } as any)
  })

  it('should render page title', () => {
    vi.mocked(useListSchedules).mockReturnValue({ data: { schedules: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Schedules />, { wrapper: createWrapper() })
    expect(screen.getByText('Task Schedules')).toBeInTheDocument()
  })

  it('should show Create Schedule button', () => {
    vi.mocked(useListSchedules).mockReturnValue({ data: { schedules: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Schedules />, { wrapper: createWrapper() })
    expect(screen.getByText('Create Schedule')).toBeInTheDocument()
  })

  it('should display schedules in a table', async () => {
    vi.mocked(useListSchedules).mockReturnValue({
      data: {
        schedules: [
          { id: 1, task_id: 1, task_name: 'Sync Users', cron_expression: '0 2 * * *', is_active: true, last_run_date: null, next_run_date: null, created_at: new Date().toISOString() },
        ],
        total_count: 1,
      },
      isLoading: false,
      isError: false,
    } as any)

    render(<Schedules />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Sync Users')).toBeInTheDocument()
      expect(screen.getByText('0 2 * * *')).toBeInTheDocument()
      expect(screen.getByText('Active')).toBeInTheDocument()
    })
  })

  it('should show empty state when no schedules', async () => {
    vi.mocked(useListSchedules).mockReturnValue({ data: { schedules: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Schedules />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('No schedules found')).toBeInTheDocument()
    })
  })

  it('should handle error state', () => {
    vi.mocked(useListSchedules).mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
    render(<Schedules />, { wrapper: createWrapper() })
    expect(screen.getByText(/Failed to load schedules/)).toBeInTheDocument()
  })

  it('should show filter controls', () => {
    vi.mocked(useListSchedules).mockReturnValue({ data: { schedules: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Schedules />, { wrapper: createWrapper() })
    expect(screen.getByText('Filter:')).toBeInTheDocument()
    expect(screen.getByText('Per Page:')).toBeInTheDocument()
  })
})
