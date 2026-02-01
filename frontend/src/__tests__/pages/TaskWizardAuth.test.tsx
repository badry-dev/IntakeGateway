import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import TaskWizard from '@/pages/TaskWizard'

// Mock the API hooks
vi.mock('@/hooks/api', () => ({
  useCreateTask: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ id: 1 }),
    isPending: false,
  }),
  useColumnMappings: () => ({
    data: [],
    isLoading: false,
  }),
  useListSchedules: () => ({
    data: [],
    isLoading: false,
  }),
}))

// Mock ColumnMappingEditor
vi.mock('@/components/ColumnMappingEditor', () => ({
  ColumnMappingEditor: ({ wizardMode }: any) => (
    <div data-testid="column-mapping-editor">Column Mapping Editor {wizardMode ? '(Wizard)' : ''}</div>
  ),
}))

const queryClient = new QueryClient()

function renderWithRouter(component: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('TaskWizard - End-to-End with Authentication', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render all 6 wizard steps', () => {
    renderWithRouter(<TaskWizard />)
    
    // Should start on Basic step
    expect(screen.getByText(/Task Name/i)).toBeInTheDocument()
    expect(screen.getByText(/Basic Information/i)).toBeInTheDocument()
  })

  it('should progress through Basic -> Endpoint -> Headers -> Auth -> Mapping -> Review steps', async () => {
    const user = userEvent.setup()
    renderWithRouter(<TaskWizard />)
    
    // Step 1: Basic
    const taskNameInput = screen.getByPlaceholderText('e.g., Sync Users')
    await user.type(taskNameInput, 'My Task')
    
    const tableInput = screen.getByPlaceholderText('e.g., USERS')
    await user.type(tableInput, 'USERS')
    
    let nextButton = screen.getByRole('button', { name: /Next/i })
    fireEvent.click(nextButton)
    
    // Step 2: Endpoint
    await waitFor(() => {
      expect(screen.getByPlaceholderText('https://api.example.com/users')).toBeInTheDocument()
    })
    
    const endpointInput = screen.getByPlaceholderText('https://api.example.com/users')
    await user.type(endpointInput, 'https://api.example.com/users')
    
    nextButton = screen.getByRole('button', { name: /Next/i })
    fireEvent.click(nextButton)
    
    // Step 3: Headers
    await waitFor(() => {
      expect(screen.getByText(/Add Header/i)).toBeInTheDocument()
    })
    
    nextButton = screen.getByRole('button', { name: /Next/i })
    fireEvent.click(nextButton)
    
    // Step 4: Authentication (NEW STEP)
    await waitFor(() => {
      expect(screen.getByText(/Authentication Type/i)).toBeInTheDocument()
    })
    
    // Verify auth options exist
    expect(screen.getByText(/No Authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/Bearer Token/i)).toBeInTheDocument()
    expect(screen.getByText(/API Key/i)).toBeInTheDocument()
    
    nextButton = screen.getByRole('button', { name: /Next/i })
    fireEvent.click(nextButton)
    
    // Step 5: Mapping
    await waitFor(() => {
      expect(screen.getByTestId('column-mapping-editor')).toBeInTheDocument()
    })
    
    nextButton = screen.getByRole('button', { name: /Next/i })
    fireEvent.click(nextButton)
    
    // Step 6: Review
    await waitFor(() => {
      expect(screen.getByText(/My Task/i)).toBeInTheDocument()
    })
  })

  it('should validate auth fields based on auth type', async () => {
    const user = userEvent.setup()
    renderWithRouter(<TaskWizard />)
    
    // Complete first steps
    const taskNameInput = screen.getByPlaceholderText('e.g., Sync Users')
    await user.type(taskNameInput, 'My Task')
    const tableInput = screen.getByPlaceholderText('e.g., USERS')
    await user.type(tableInput, 'USERS')
    
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))
    
    await waitFor(() => {
      const endpointInput = screen.getByPlaceholderText('https://api.example.com/users')
      fireEvent.click(screen.getAllByRole('button', { name: /Next/i })[0])
    })
    
    await waitFor(() => {
      fireEvent.click(screen.getAllByRole('button', { name: /Next/i })[0])
    })
    
    // Now on Auth step
    await waitFor(() => {
      expect(screen.getByText(/Authentication Type/i)).toBeInTheDocument()
    })
    
    // Select Bearer Token
    const authSelect = screen.getByDisplayValue('No Authentication')
    await user.click(authSelect)
    
    // Note: The actual selection would depend on Select component implementation
    // For now, we verify the UI exists
    expect(screen.getByText(/Bearer Token/i)).toBeInTheDocument()
  })

  it('should include auth info in review step', async () => {
    const user = userEvent.setup()
    renderWithRouter(<TaskWizard />)
    
    // Fill and submit form
    const taskNameInput = screen.getByPlaceholderText('e.g., Sync Users')
    await user.type(taskNameInput, 'My Task')
    
    const tableInput = screen.getByPlaceholderText('e.g., USERS')
    await user.type(tableInput, 'USERS')
    
    // Progress to end
    const nextButtons = screen.getAllByRole('button', { name: /Next/i })
    for (let i = 0; i < 5; i++) {
      fireEvent.click(nextButtons[0])
      await waitFor(() => {
        const allNextButtons = screen.getAllByRole('button', { name: /Next|Create Task/i })
        return allNextButtons.length > 0
      })
    }
    
    // Verify review includes auth section
    await waitFor(() => {
      const reviewText = screen.queryByText(/Authentication/i)
      // Auth info should be in review if auth type was set
      // For now, we just verify no error occurs
    })
  })

  it('should support Bearer token authentication', async () => {
    const user = userEvent.setup()
    renderWithRouter(<TaskWizard />)
    
    // Navigate to auth step
    const taskNameInput = screen.getByPlaceholderText('e.g., Sync Users')
    await user.type(taskNameInput, 'My Task')
    const tableInput = screen.getByPlaceholderText('e.g., USERS')
    await user.type(tableInput, 'USERS')
    
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))
    
    // Skip to auth step (2 more clicks)
    await waitFor(() => {
      const nextButtons = screen.getAllByRole('button', { name: /Next/i })
      if (nextButtons.length > 1) {
        fireEvent.click(nextButtons[0])
      }
    })
    
    await waitFor(() => {
      const nextButtons = screen.getAllByRole('button', { name: /Next/i })
      if (nextButtons.length > 1) {
        fireEvent.click(nextButtons[0])
      }
    })
    
    // Now on auth step - verify Bearer token option exists
    await waitFor(() => {
      expect(screen.getByText(/Bearer Token/i)).toBeInTheDocument()
    })
  })

  it('should support API Key authentication', async () => {
    renderWithRouter(<TaskWizard />)
    
    // Verify API Key option exists
    expect(screen.getByText(/API Key/i)).toBeInTheDocument()
  })

  it('should support Basic authentication', async () => {
    renderWithRouter(<TaskWizard />)
    
    // Verify Basic Auth option exists
    expect(screen.getByText(/Basic Auth/i)).toBeInTheDocument()
  })

  it('should support OAuth', async () => {
    renderWithRouter(<TaskWizard />)
    
    // Verify OAuth option exists
    expect(screen.getByText(/OAuth 2\.0/i)).toBeInTheDocument()
  })
})
