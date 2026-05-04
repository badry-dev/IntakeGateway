/**
 * Component tests for ColumnMappingEditor
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'

vi.mock('@/hooks/api', () => ({
  useConnections: vi.fn().mockReturnValue({ data: { connections: [], total_count: 0 }, isLoading: false, isError: false }),
  useBackfillTask: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useOracleColumns: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  apiClient: {
    previewMappingFieldsStandalone: vi.fn(),
  },
}))

import { useOracleColumns } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('ColumnMappingEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useOracleColumns).mockReturnValue({ data: undefined, isLoading: false, error: null } as any)
  })

  it('should render sample data section', () => {
    render(<ColumnMappingEditor wizardMode taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'TEST' } as any} />, { wrapper: createWrapper() })
    expect(screen.getByText('Step 1: Load Sample Data')).toBeInTheDocument()
  })

  it('should show Auto-Fetch and Manual Paste tabs', () => {
    render(<ColumnMappingEditor wizardMode taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'TEST' } as any} />, { wrapper: createWrapper() })
    expect(screen.getByText('Auto-Fetch')).toBeInTheDocument()
    expect(screen.getByText('Manual Paste')).toBeInTheDocument()
  })

  it('should show Fetch Sample from API button', () => {
    render(<ColumnMappingEditor wizardMode taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'TEST' } as any} />, { wrapper: createWrapper() })
    expect(screen.getByText('Fetch Sample from API')).toBeInTheDocument()
  })

  it('should switch to manual paste tab', async () => {
    const user = userEvent.setup()
    render(<ColumnMappingEditor wizardMode taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'TEST' } as any} />, { wrapper: createWrapper() })

    await user.click(screen.getByText('Manual Paste'))
    expect(screen.getByPlaceholderText(/Paste JSON/)).toBeInTheDocument()
    expect(screen.getByText('Parse JSON')).toBeInTheDocument()
  })

  it('should display existing mappings', () => {
    const existingMappings = [
      { source_field: 'name', dest_column: 'USER_NAME', transform_rules: [], is_active: true },
    ]
    render(
      <ColumnMappingEditor
        wizardMode
        taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'TEST' } as any}
        existingMappings={existingMappings}
      />,
      { wrapper: createWrapper() }
    )
    // Existing mappings are loaded into state — Save/Clear actions become available
    expect(screen.getByText('Save Mappings')).toBeInTheDocument()
    expect(screen.getByText('Clear All')).toBeInTheDocument()
  })

  it('should show table name in debug info', () => {
    render(<ColumnMappingEditor wizardMode taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'MY_TABLE' } as any} />, { wrapper: createWrapper() })
    expect(screen.getByText(/MY_TABLE/)).toBeInTheDocument()
  })

  it('should show save and clear buttons when mappings exist', () => {
    const existingMappings = [
      { source_field: 'id', dest_column: 'ID', is_active: true },
    ]
    render(
      <ColumnMappingEditor
        wizardMode
        taskFormData={{ name: 'Test', endpoint_path: 'https://test.com', http_method: 'GET', dest_table: 'TEST' } as any}
        existingMappings={existingMappings}
      />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByText('Save Mappings')).toBeInTheDocument()
    expect(screen.getByText('Clear All')).toBeInTheDocument()
  })
})
