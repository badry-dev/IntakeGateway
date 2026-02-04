import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConnectionEditor } from '@/components/ConnectionEditor'

// Mock the API client
vi.mock('@/api/client', () => ({
  apiClient: {
    testConnection: vi.fn(),
  },
}))

import { apiClient } from '@/api/client'

const mockConnection = {
  id: 'conn-1',
  name: 'Test DB',
  db_type: 'oracle' as const,
  host: 'localhost',
  port: 1521,
  username: 'admin',
  service_name: 'ORCL',
  is_default: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function renderConnectionEditor(props: Partial<React.ComponentProps<typeof ConnectionEditor>> = {}) {
  const queryClient = createQueryClient()
  const defaultProps = {
    onSave: vi.fn().mockResolvedValue(undefined),
    ...props,
  }

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <ConnectionEditor {...defaultProps} />
      </QueryClientProvider>
    ),
    onSave: defaultProps.onSave,
  }
}

describe('ConnectionEditor Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Create Mode', () => {
    it('renders create form with empty fields', () => {
      renderConnectionEditor()

      expect(screen.getByText('New Connection')).toBeInTheDocument()
      expect(screen.getByLabelText('Connection Name')).toHaveValue('')
      expect(screen.getByLabelText('Host')).toHaveValue('')
      expect(screen.getByLabelText('Username')).toHaveValue('')
    })

    it('has Create button instead of Update', () => {
      renderConnectionEditor()

      expect(screen.getByRole('button', { name: 'Create' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Update' })).not.toBeInTheDocument()
    })

    it('does not show Delete button in create mode', () => {
      renderConnectionEditor()

      expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
    })

    it('requires password for new connections', () => {
      const { onSave } = renderConnectionEditor()

      // Fill all fields except password
      fireEvent.change(screen.getByLabelText('Connection Name'), {
        target: { value: 'Test DB' },
      })
      fireEvent.change(screen.getByLabelText('Host'), {
        target: { value: 'localhost' },
      })
      fireEvent.change(screen.getByLabelText('Username'), {
        target: { value: 'admin' },
      })
      fireEvent.change(screen.getByLabelText('Service Name'), {
        target: { value: 'ORCL' },
      })

      // Create button should be disabled without password
      const createButton = screen.getByRole('button', { name: 'Create' })
      expect(createButton).toBeDisabled()
    })
  })

  describe('Edit Mode', () => {
    it('renders edit form with existing values', () => {
      renderConnectionEditor({ connection: mockConnection })

      expect(screen.getByText('Edit Connection')).toBeInTheDocument()
      expect(screen.getByLabelText('Connection Name')).toHaveValue('Test DB')
      expect(screen.getByLabelText('Host')).toHaveValue('localhost')
      expect(screen.getByLabelText('Username')).toHaveValue('admin')
      expect(screen.getByLabelText('Service Name')).toHaveValue('ORCL')
    })

    it('has Update button instead of Create', () => {
      renderConnectionEditor({ connection: mockConnection })

      expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Create' })).not.toBeInTheDocument()
    })

    it('shows Delete button in edit mode with onDelete', () => {
      renderConnectionEditor({
        connection: mockConnection,
        onDelete: vi.fn(),
      })

      expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
    })

    it('password field shows placeholder in edit mode', () => {
      renderConnectionEditor({ connection: mockConnection })

      const passwordInput = screen.getByLabelText(/Password/i)
      expect(passwordInput).toHaveAttribute('placeholder', '********')
    })

    it('does not require password in edit mode', () => {
      renderConnectionEditor({ connection: mockConnection })

      // Update button should be enabled without changing password
      const updateButton = screen.getByRole('button', { name: 'Update' })
      expect(updateButton).not.toBeDisabled()
    })

    it('disables db_type selector in edit mode', () => {
      renderConnectionEditor({ connection: mockConnection })

      // The select trigger should indicate it's disabled
      expect(
        screen.getByText('Database type cannot be changed after creation')
      ).toBeInTheDocument()
    })
  })

  describe('Database Type Selection', () => {
    it('defaults to Oracle', () => {
      renderConnectionEditor()

      expect(screen.getByLabelText('Service Name')).toBeInTheDocument()
      expect(screen.queryByLabelText('Database')).not.toBeInTheDocument()
    })

    it('shows Service Name field for Oracle', () => {
      renderConnectionEditor()

      expect(screen.getByLabelText('Service Name')).toBeInTheDocument()
    })

    it('updates port when db_type changes', async () => {
      renderConnectionEditor()

      // Default port for Oracle is 1521
      expect(screen.getByLabelText('Port')).toHaveValue(1521)

      // Change to PostgreSQL
      const dbTypeSelect = screen.getByRole('combobox')
      fireEvent.click(dbTypeSelect)

      await waitFor(() => {
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('PostgreSQL'))

      // Port should change to 5432
      await waitFor(() => {
        expect(screen.getByLabelText('Port')).toHaveValue(5432)
      })

      // Should now show Database field instead of Service Name
      expect(screen.getByLabelText('Database')).toBeInTheDocument()
      expect(screen.queryByLabelText('Service Name')).not.toBeInTheDocument()
    })
  })

  describe('Test Connection', () => {
    it('calls test connection API', async () => {
      vi.mocked(apiClient.testConnection).mockResolvedValue({
        success: true,
        message: 'Connection successful',
        latency_ms: 50,
        server_version: 'Oracle 19c',
      })

      renderConnectionEditor()

      // Fill required fields
      fireEvent.change(screen.getByLabelText('Connection Name'), {
        target: { value: 'Test' },
      })
      fireEvent.change(screen.getByLabelText('Host'), {
        target: { value: 'localhost' },
      })
      fireEvent.change(screen.getByLabelText('Username'), {
        target: { value: 'admin' },
      })
      fireEvent.change(screen.getByLabelText(/Password/i), {
        target: { value: 'secret' },
      })
      fireEvent.change(screen.getByLabelText('Service Name'), {
        target: { value: 'ORCL' },
      })

      // Click test button
      fireEvent.click(screen.getByRole('button', { name: /Test Connection/i }))

      await waitFor(() => {
        expect(apiClient.testConnection).toHaveBeenCalled()
      })
    })

    it('shows success result', async () => {
      vi.mocked(apiClient.testConnection).mockResolvedValue({
        success: true,
        message: 'Connection successful',
        latency_ms: 50,
        server_version: 'Oracle 19c',
      })

      renderConnectionEditor()

      // Fill required fields
      fireEvent.change(screen.getByLabelText('Host'), {
        target: { value: 'localhost' },
      })
      fireEvent.change(screen.getByLabelText('Username'), {
        target: { value: 'admin' },
      })
      fireEvent.change(screen.getByLabelText(/Password/i), {
        target: { value: 'secret' },
      })

      fireEvent.click(screen.getByRole('button', { name: /Test Connection/i }))

      await waitFor(() => {
        expect(screen.getByText('Connection successful')).toBeInTheDocument()
      })

      expect(screen.getByText(/Latency: 50ms/)).toBeInTheDocument()
    })

    it('shows failure result', async () => {
      vi.mocked(apiClient.testConnection).mockResolvedValue({
        success: false,
        message: 'Connection refused',
      })

      renderConnectionEditor()

      // Fill required fields
      fireEvent.change(screen.getByLabelText('Host'), {
        target: { value: 'localhost' },
      })
      fireEvent.change(screen.getByLabelText('Username'), {
        target: { value: 'admin' },
      })
      fireEvent.change(screen.getByLabelText(/Password/i), {
        target: { value: 'secret' },
      })

      fireEvent.click(screen.getByRole('button', { name: /Test Connection/i }))

      await waitFor(() => {
        expect(screen.getByText('Connection refused')).toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    it('calls onSave with form data on submit', async () => {
      const { onSave } = renderConnectionEditor()

      // Fill all required fields
      fireEvent.change(screen.getByLabelText('Connection Name'), {
        target: { value: 'New DB' },
      })
      fireEvent.change(screen.getByLabelText('Host'), {
        target: { value: 'db.example.com' },
      })
      fireEvent.change(screen.getByLabelText('Username'), {
        target: { value: 'dbuser' },
      })
      fireEvent.change(screen.getByLabelText(/Password/i), {
        target: { value: 'dbpass' },
      })
      fireEvent.change(screen.getByLabelText('Service Name'), {
        target: { value: 'PROD' },
      })

      fireEvent.click(screen.getByRole('button', { name: 'Create' }))

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'New DB',
            host: 'db.example.com',
            username: 'dbuser',
            password: 'dbpass',
            service_name: 'PROD',
          })
        )
      })
    })
  })

  describe('Delete Confirmation', () => {
    it('shows delete confirmation on delete click', async () => {
      const onDelete = vi.fn().mockResolvedValue(undefined)
      renderConnectionEditor({
        connection: mockConnection,
        onDelete,
      })

      fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Confirm Delete' })).toBeInTheDocument()
      })
    })

    it('calls onDelete when confirmed', async () => {
      const onDelete = vi.fn().mockResolvedValue(undefined)
      renderConnectionEditor({
        connection: mockConnection,
        onDelete,
      })

      fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Confirm Delete' })).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('button', { name: 'Confirm Delete' }))

      await waitFor(() => {
        expect(onDelete).toHaveBeenCalled()
      })
    })

    it('hides confirmation when cancelled', async () => {
      const onDelete = vi.fn()
      renderConnectionEditor({
        connection: mockConnection,
        onDelete,
      })

      fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Confirm Delete' })).toBeInTheDocument()
      })

      // Click the cancel button (second Cancel button in delete confirmation)
      const cancelButtons = screen.getAllByRole('button', { name: 'Cancel' })
      fireEvent.click(cancelButtons[cancelButtons.length - 1])

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: 'Confirm Delete' })).not.toBeInTheDocument()
      })

      expect(onDelete).not.toHaveBeenCalled()
    })
  })

  describe('Cancel Button', () => {
    it('calls onCancel when cancel clicked', () => {
      const onCancel = vi.fn()
      renderConnectionEditor({ onCancel })

      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

      expect(onCancel).toHaveBeenCalled()
    })

    it('does not show cancel button when onCancel not provided', () => {
      renderConnectionEditor()

      // There should only be Test Connection and Create buttons
      const buttons = screen.getAllByRole('button')
      const buttonNames = buttons.map((b) => b.textContent)

      expect(buttonNames).not.toContain('Cancel')
    })
  })
})
