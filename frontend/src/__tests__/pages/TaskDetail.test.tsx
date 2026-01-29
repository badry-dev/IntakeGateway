import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { TaskDetail } from '@/pages/TaskDetail'

vi.mock('@/hooks/api', () => ({
  useTask: vi.fn(),
  usePatchTask: vi.fn(),
  useDeleteTask: vi.fn(),
}))

import { useTask, usePatchTask, useDeleteTask } from '@/hooks/api'

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/tasks/:id" element={children} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('TaskDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render task detail heading', () => {
    vi.mocked(useTask).mockReturnValue({
      data: {
        id: 'task-1',
        name: 'Test Task',
        description: 'Test description',
        endpoint_url: 'https://api.example.com',
        method: 'GET',
        table_name: 'test_table',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Task Details/i)).toBeInTheDocument()
  })

  it('should display loading state', () => {
    vi.mocked(useTask).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })

  it('should display task information when loaded', async () => {
    vi.mocked(useTask).mockReturnValue({
      data: {
        id: 'task-1',
        name: 'Sync Users',
        description: 'Sync user data',
        endpoint_url: 'https://api.example.com/users',
        method: 'GET',
        table_name: 'users',
        is_active: true,
        created_at: '2024-01-15T10:00:00Z',
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByText(/Sync Users/)).toBeInTheDocument()
      expect(screen.getByText(/Sync user data/)).toBeInTheDocument()
      expect(screen.getByText(/https:\/\/api.example.com\/users/)).toBeInTheDocument()
    })
  })

  it('should have Copy ID button', async () => {
    vi.mocked(useTask).mockReturnValue({
      data: {
        id: 'task-1',
        name: 'Test Task',
        description: 'Test',
        endpoint_url: 'https://api.example.com',
        method: 'GET',
        table_name: 'test_table',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Copy ID/i })).toBeInTheDocument()
    })
  })

  it('should have Edit button that opens modal', async () => {
    vi.mocked(useTask).mockReturnValue({
      data: {
        id: 'task-1',
        name: 'Test Task',
        description: 'Test',
        endpoint_url: 'https://api.example.com',
        method: 'GET',
        table_name: 'test_table',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument()
    })
  })

  it('should have Delete button', async () => {
    vi.mocked(useTask).mockReturnValue({
      data: {
        id: 'task-1',
        name: 'Test Task',
        description: 'Test',
        endpoint_url: 'https://api.example.com',
        method: 'GET',
        table_name: 'test_table',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument()
    })
  })

  it('should handle error state', () => {
    vi.mocked(useTask).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Task not found'),
    } as any)

    vi.mocked(usePatchTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    vi.mocked(useDeleteTask).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any)

    render(<TaskDetail />, { wrapper: createWrapper() })
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument()
  })
})
