import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { TaskWizard } from '@/pages/TaskWizard'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn().mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false }),
  useBackfillTask: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useCreateTask: vi.fn(),
  useCreateMappings: vi.fn(),
  useOracleColumns: vi.fn(),
}))

vi.mock('@/components/ColumnMappingEditor', () => ({
  ColumnMappingEditor: () => <div data-testid="column-mapping-editor">ColumnMappingEditor</div>,
}))

import { useCreateTask, useCreateMappings, useOracleColumns } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('TaskWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useCreateTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useCreateMappings).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useOracleColumns).mockReturnValue({ data: undefined, isLoading: false } as any)
  })

  it('should render wizard heading', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByText('Create New Task')).toBeInTheDocument()
  })

  it('should start on basic info step', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByPlaceholderText(/Sync Users/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Describe what this task does/)).toBeInTheDocument()
  })

  it('should have Previous button disabled on first step', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  })

  it('should have Next button disabled when required fields empty', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('should keep Next disabled until all required fields filled including connection', async () => {
    const user = userEvent.setup()
    render(<TaskWizard />, { wrapper: createWrapper() })

    await user.type(screen.getByPlaceholderText(/Sync Users/), 'My Task')
    await user.type(screen.getByPlaceholderText(/users, products/), 'MY_TABLE')
    // Connection not selected — Next remains disabled
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('should show Back button', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByText('Back')).toBeInTheDocument()
  })

  it('should display steps indicator', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByText('Basic Info')).toBeInTheDocument()
    expect(screen.getByText('Endpoint')).toBeInTheDocument()
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.getByText('Review')).toBeInTheDocument()
  })
})
