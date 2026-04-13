import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { TaskWizard } from '@/pages/TaskWizard'

vi.mock('@/hooks/api', () => ({
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

async function navigateToAuthStep(user: ReturnType<typeof userEvent.setup>) {
  // Step 1: Basic Info
  await user.type(screen.getByPlaceholderText(/Sync Users/), 'Auth Task')
  await user.type(screen.getByPlaceholderText(/users, products/), 'AUTH_TABLE')
  await user.click(screen.getByText('Next'))

  // Step 2: Endpoint
  await user.type(screen.getByPlaceholderText(/api.example.com/), 'https://api.test.com/data')
  await user.click(screen.getByText('Next'))

  // Step 3: Headers
  await user.click(screen.getByText('Next'))

  // Now on Step 4: Authentication
}

describe('TaskWizard Auth Step', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useCreateTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useCreateMappings).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useOracleColumns).mockReturnValue({ data: undefined, isLoading: false } as any)
  })

  it('should show auth type selector on auth step', async () => {
    const user = userEvent.setup()
    render(<TaskWizard />, { wrapper: createWrapper() })
    await navigateToAuthStep(user)

    await waitFor(() => {
      expect(screen.getByText('Authentication Type')).toBeInTheDocument()
    })
  })

  it('should show no-auth message by default', async () => {
    const user = userEvent.setup()
    render(<TaskWizard />, { wrapper: createWrapper() })
    await navigateToAuthStep(user)

    await waitFor(() => {
      expect(screen.getByText(/No authentication will be used/)).toBeInTheDocument()
    })
  })

  it('should display all wizard steps', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    expect(screen.getByText('Basic Info')).toBeInTheDocument()
    expect(screen.getByText('Endpoint')).toBeInTheDocument()
    expect(screen.getByText('Headers & Body')).toBeInTheDocument()
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.getByText('Mapping')).toBeInTheDocument()
    expect(screen.getByText('Review')).toBeInTheDocument()
  })
})
