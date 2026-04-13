import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConnectionEditor } from '@/components/ConnectionEditor'

vi.mock('@/hooks/api', () => ({
  useTestConnection: vi.fn(),
}))

import { useTestConnection } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('ConnectionEditor', () => {
  const mockOnSave = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useTestConnection).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as any)
  })

  describe('Create mode', () => {
    it('should render empty form for new connection', () => {
      render(<ConnectionEditor onSave={mockOnSave} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByPlaceholderText(/Production Database/)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/db.example.com/)).toBeInTheDocument()
    })

    it('should show Create button', () => {
      render(<ConnectionEditor onSave={mockOnSave} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByText('Create')).toBeInTheDocument()
    })

    it('should show Test Connection button', () => {
      render(<ConnectionEditor onSave={mockOnSave} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByText('Test Connection')).toBeInTheDocument()
    })

    it('should show Cancel button when onCancel provided', () => {
      render(<ConnectionEditor onSave={mockOnSave} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByText('Cancel')).toBeInTheDocument()
    })
  })

  describe('Edit mode', () => {
    const mockConnection = {
      id: 'conn-1', name: 'Prod DB', db_type: 'oracle' as const, host: 'db.prod.com', port: 1521,
      username: 'admin', service_name: 'ORCL', is_default: false,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }

    it('should pre-populate form with connection data', () => {
      render(<ConnectionEditor connection={mockConnection} onSave={mockOnSave} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByDisplayValue('Prod DB')).toBeInTheDocument()
      expect(screen.getByDisplayValue('db.prod.com')).toBeInTheDocument()
      expect(screen.getByDisplayValue('admin')).toBeInTheDocument()
    })

    it('should show Update button in edit mode', () => {
      render(<ConnectionEditor connection={mockConnection} onSave={mockOnSave} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByText('Update')).toBeInTheDocument()
    })

    it('should show Delete button when onDelete provided', () => {
      const mockOnDelete = vi.fn()
      render(<ConnectionEditor connection={mockConnection} onSave={mockOnSave} onDelete={mockOnDelete} onCancel={mockOnCancel} />, { wrapper: createWrapper() })
      expect(screen.getByText('Delete')).toBeInTheDocument()
    })

    it('should show delete confirmation on Delete click', async () => {
      const user = userEvent.setup()
      const mockOnDelete = vi.fn()
      render(<ConnectionEditor connection={mockConnection} onSave={mockOnSave} onDelete={mockOnDelete} onCancel={mockOnCancel} />, { wrapper: createWrapper() })

      await user.click(screen.getByText('Delete'))
      expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
    })
  })

  describe('Database type', () => {
    it('should show Service Name field for Oracle', () => {
      render(<ConnectionEditor onSave={mockOnSave} />, { wrapper: createWrapper() })
      expect(screen.getByPlaceholderText(/ORCL/)).toBeInTheDocument()
    })
  })
})
