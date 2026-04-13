/**
 * Integration tests for TaskWizard mapping step
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { TaskWizard } from '@/pages/TaskWizard'

vi.mock('@/hooks/api', () => ({
  useCreateTask: vi.fn(),
  useCreateMappings: vi.fn(),
  useOracleColumns: vi.fn(),
}))

vi.mock('@/components/ColumnMappingEditor', () => ({
  ColumnMappingEditor: () => <div data-testid="column-mapping-editor">ColumnMappingEditor Mock</div>,
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

describe('TaskWizard Mapping Step', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useCreateTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useCreateMappings).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useOracleColumns).mockReturnValue({ data: undefined, isLoading: false } as any)
  })

  it('should show all wizard steps', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByText('Basic Info')).toBeInTheDocument()
    expect(screen.getByText('Endpoint')).toBeInTheDocument()
    expect(screen.getByText('Headers & Body')).toBeInTheDocument()
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.getByText('Mapping')).toBeInTheDocument()
    expect(screen.getByText('Review')).toBeInTheDocument()
  })

  it('should navigate forward through steps', async () => {
    const user = userEvent.setup()
    render(<TaskWizard />, { wrapper: createWrapper() })

    // Step 1: Fill basic info
    await user.type(screen.getByPlaceholderText(/Sync Users/), 'Test Task')
    await user.type(screen.getByPlaceholderText(/users, products/), 'TEST_TABLE')
    await user.click(screen.getByText('Next'))

    // Step 2: Endpoint - should now show endpoint fields
    expect(screen.getByPlaceholderText(/api.example.com/)).toBeInTheDocument()
  })

  it('should not allow navigation without required fields', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    // Next should be disabled without name and table
    expect(screen.getByText('Next')).toBeDisabled()
  })

  it('should show Previous button disabled on first step', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByText('Previous')).toBeDisabled()
  })
})
