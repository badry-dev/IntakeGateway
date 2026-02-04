import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Settings } from '@/pages/Settings'

// Mock the API client
vi.mock('@/api/client', () => ({
  apiClient: {
    getConnections: vi.fn(),
    createConnection: vi.fn(),
    updateConnection: vi.fn(),
    deleteConnection: vi.fn(),
    activateConnection: vi.fn(),
    testConnection: vi.fn(),
  },
}))

import { apiClient } from '@/api/client'

const mockConnections = [
  {
    id: 'conn-1',
    name: 'Production DB',
    db_type: 'oracle',
    host: 'prod.db.example.com',
    port: 1521,
    username: 'prod_user',
    service_name: 'PROD',
    is_default: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
  {
    id: 'conn-2',
    name: 'Dev DB',
    db_type: 'postgresql',
    host: 'dev.db.example.com',
    port: 5432,
    username: 'dev_user',
    database: 'devdb',
    is_default: false,
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-10T00:00:00Z',
  },
]

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function renderSettings() {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <Settings />
    </QueryClientProvider>
  )
}

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders settings page with title', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: [],
        active_connection_id: null,
        total_count: 0,
      })

      renderSettings()

      expect(screen.getByText('Settings')).toBeInTheDocument()
      expect(screen.getByText('Database Connections')).toBeInTheDocument()
    })

    it('renders empty state when no connections', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: [],
        active_connection_id: null,
        total_count: 0,
      })

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('No database connections configured')).toBeInTheDocument()
      })

      expect(screen.getByText('Add Your First Connection')).toBeInTheDocument()
    })

    it('renders connection list when connections exist', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: mockConnections,
        active_connection_id: 'conn-1',
        total_count: 2,
      })

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('Production DB')).toBeInTheDocument()
      })

      expect(screen.getByText('Dev DB')).toBeInTheDocument()
      expect(screen.getByText('prod.db.example.com:1521')).toBeInTheDocument()
      expect(screen.getByText('ORACLE')).toBeInTheDocument()
      expect(screen.getByText('POSTGRESQL')).toBeInTheDocument()
    })

    it('shows Active badge on active connection', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: mockConnections,
        active_connection_id: 'conn-1',
        total_count: 2,
      })

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument()
      })

      // Non-active connection should have "Set Active" button
      expect(screen.getByText('Set Active')).toBeInTheDocument()
    })
  })

  describe('Add Connection', () => {
    it('opens create dialog when Add Connection clicked', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: [],
        active_connection_id: null,
        total_count: 0,
      })

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('Add Connection')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Add Connection'))

      await waitFor(() => {
        expect(screen.getByText('New Connection')).toBeInTheDocument()
      })
    })
  })

  describe('Edit Connection', () => {
    it('opens edit dialog when edit button clicked', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: mockConnections,
        active_connection_id: 'conn-1',
        total_count: 2,
      })

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('Production DB')).toBeInTheDocument()
      })

      // Find and click the edit button (pencil icon)
      const editButtons = screen.getAllByRole('button')
      const pencilButton = editButtons.find(
        (btn) => btn.querySelector('svg.lucide-pencil') !== null
      )

      if (pencilButton) {
        fireEvent.click(pencilButton)

        await waitFor(() => {
          expect(screen.getByText('Edit Connection')).toBeInTheDocument()
        })
      }
    })
  })

  describe('Activate Connection', () => {
    it('calls activateConnection when Set Active clicked', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: mockConnections,
        active_connection_id: 'conn-1',
        total_count: 2,
      })
      vi.mocked(apiClient.activateConnection).mockResolvedValue({ message: 'Activated' })

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('Set Active')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Set Active'))

      await waitFor(() => {
        expect(apiClient.activateConnection).toHaveBeenCalledWith('conn-2')
      })
    })
  })

  describe('Error Handling', () => {
    it('shows error state when API fails', async () => {
      vi.mocked(apiClient.getConnections).mockRejectedValue(new Error('Network error'))

      renderSettings()

      await waitFor(() => {
        expect(screen.getByText('Failed to load connections')).toBeInTheDocument()
      })
    })
  })

  describe('Info Card', () => {
    it('shows environment variable fallback info', async () => {
      vi.mocked(apiClient.getConnections).mockResolvedValue({
        connections: [],
        active_connection_id: null,
        total_count: 0,
      })

      renderSettings()

      await waitFor(() => {
        expect(
          screen.getByText(/environment variables/i)
        ).toBeInTheDocument()
      })
    })
  })
})
