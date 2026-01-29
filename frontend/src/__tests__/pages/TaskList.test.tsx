import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { TaskList } from '@/pages/TaskList'

vi.mock('@/hooks/api', () => ({
  useTasks: vi.fn(),
  useTriggerRun: vi.fn(),
  useDeleteTask: vi.fn(),
}))

import { useTasks, useTriggerRun, useDeleteTask } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('TaskList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render tasks page heading', () => {
    vi.mocked(useTasks).mockReturnValue({
      data: { results: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Tasks/)).toBeInTheDocument()
  })

  it('should display loading state', () => {
    vi.mocked(useTasks).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('should display empty state when no tasks', async () => {
    vi.mocked(useTasks).mockReturnValue({
      data: { results: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/No tasks yet/i)).toBeInTheDocument()
    })
  })

  it('should display task cards when data loads', async () => {
    vi.mocked(useTasks).mockReturnValue({
      data: {
        results: [
          {
            id: 'task-1',
            name: 'Sync Users',
            description: 'Sync user data from API',
            endpoint_url: 'https://api.example.com/users',
            method: 'GET',
            table_name: 'users',
            is_active: true,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/Sync Users/)).toBeInTheDocument()
      expect(screen.getByText(/Sync user data from API/)).toBeInTheDocument()
    })
  })

  it('should display Run, Edit, and Delete buttons for each task', async () => {
    vi.mocked(useTasks).mockReturnValue({
      data: {
        results: [
          {
            id: 'task-1',
            name: 'Test Task',
            description: 'Test',
            endpoint_url: 'https://api.example.com/test',
            method: 'GET',
            table_name: 'test_table',
            is_active: true,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Run/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument()
    })
  })

  it('should show New Task button link', () => {
    vi.mocked(useTasks).mockReturnValue({
      data: { results: [], total: 0 },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    expect(screen.getByRole('link', { name: /New Task/i })).toHaveAttribute('href', '/tasks/new')
  })

  it('should handle API errors', () => {
    vi.mocked(useTasks).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load tasks'),
    } as any)

    vi.mocked(useTriggerRun).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskList />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument()
  })
})
