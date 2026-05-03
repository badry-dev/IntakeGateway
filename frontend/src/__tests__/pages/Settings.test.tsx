import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Settings } from '@/pages/Settings'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn(),
  useCreateConnection: vi.fn(),
  useUpdateConnection: vi.fn(),
  useDeleteConnection: vi.fn(),
}))

vi.mock('@/components/ConnectionEditor', () => ({
  ConnectionEditor: () => <div data-testid="connection-editor">ConnectionEditor</div>,
}))

import { useConnections, useCreateConnection, useUpdateConnection, useDeleteConnection } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useCreateConnection).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useUpdateConnection).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
    vi.mocked(useDeleteConnection).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
  })

  it('should render settings heading', () => {
    vi.mocked(useConnections).mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Settings />, { wrapper: createWrapper() })
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('should show Connections tab', () => {
    vi.mocked(useConnections).mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Settings />, { wrapper: createWrapper() })
    expect(screen.getAllByText('Connections').length).toBeGreaterThan(0)
  })

  it('should show empty state when no connections', async () => {
    vi.mocked(useConnections).mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Settings />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('No connections configured')).toBeInTheDocument()
      expect(screen.getByText('Add Your First Connection')).toBeInTheDocument()
    })
  })

  it('should show Add Connection button', () => {
    vi.mocked(useConnections).mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Settings />, { wrapper: createWrapper() })
    expect(screen.getByText('Add Connection')).toBeInTheDocument()
  })

  it('should display connections in a table', async () => {
    vi.mocked(useConnections).mockReturnValue({
      data: {
        connections: [
          { id: 'conn-1', name: 'Production DB', db_type: 'oracle', host: 'db.example.com', port: 1521, username: 'admin', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
        ],
        total_count: 1,
      },
      isLoading: false,
      isError: false,
    } as any)

    render(<Settings />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText('Production DB')).toBeInTheDocument()
      expect(screen.getByText('ORACLE')).toBeInTheDocument()
    })
  })

  it('should show info alert about explicit task selection', () => {
    vi.mocked(useConnections).mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false } as any)
    render(<Settings />, { wrapper: createWrapper() })
    expect(screen.getByText(/must explicitly select/i)).toBeInTheDocument()
  })
})
