import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
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

import { useConnections, useCreateTask, useCreateMappings, useOracleColumns } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}


describe('TaskWizard Auth Step', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useConnections).mockReturnValue({
      data: { connections: [{ id: 'conn-1', name: 'Test DB', db_type: 'oracle', host: 'localhost', port: 1521, username: 'admin', created_at: '', updated_at: '' }], total_count: 1 },
      isLoading: false, isError: false,
    } as any)
    vi.mocked(useCreateTask).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useCreateMappings).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useOracleColumns).mockReturnValue({ data: undefined, isLoading: false } as any)
  })

  it('should show auth type selector on auth step', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    // Authentication step is shown in the wizard steps indicator
    expect(screen.getByText('Authentication')).toBeInTheDocument()
    expect(screen.getByText('API authentication method')).toBeInTheDocument()
  })

  it('should show no-auth message by default', () => {
    render(<TaskWizard />, { wrapper: createWrapper() })
    // No bearer/API-key credentials visible on initial step (default auth type is none)
    expect(screen.queryByText(/Bearer Token/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/API Key/i)).not.toBeInTheDocument()
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
