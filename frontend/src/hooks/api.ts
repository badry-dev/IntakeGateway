import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { Task, TaskRun, TaskStats, TaskCreate, TaskUpdate } from '@/types'

// Query keys
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (skip: number, limit: number, isActive?: boolean) =>
    [...taskKeys.lists(), { skip, limit, isActive }] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: number) => [...taskKeys.details(), id] as const,
  stats: (id: number) => [...taskKeys.all, 'stats', id] as const,
}

export const runKeys = {
  all: ['runs'] as const,
  lists: () => [...runKeys.all, 'list'] as const,
  list: (taskId: number, skip: number, limit: number, status?: string) =>
    [...runKeys.lists(), { taskId, skip, limit, status }] as const,
  recent: (skip: number, limit: number) => [...runKeys.lists(), 'recent', { skip, limit }] as const,
  details: () => [...runKeys.all, 'detail'] as const,
  detail: (taskId: number, runId: number) => [...runKeys.details(), { taskId, runId }] as const,
  detailById: (runId: number) => [...runKeys.details(), runId] as const,
}

// Task hooks
export function useTasks(skip: number = 0, limit: number = 10, isActive?: boolean) {
  return useQuery({
    queryKey: taskKeys.list(skip, limit, isActive),
    queryFn: () => apiClient.getTasks(skip, limit, isActive),
    staleTime: 30000, // 30 seconds
  })
}

export function useTask(id: number) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: () => apiClient.getTask(id),
    enabled: id > 0,
    staleTime: 30000,
  })
}

export function useTaskStats(id: number) {
  return useQuery({
    queryKey: taskKeys.stats(id),
    queryFn: () => apiClient.getTaskStats(id),
    enabled: id > 0,
    staleTime: 60000,
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: TaskCreate) => apiClient.createTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TaskUpdate }) =>
      apiClient.updateTask(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

export function useDeleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiClient.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

// Task Run hooks
export function useTriggerRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: number) => apiClient.triggerRun(taskId),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: runKeys.list(taskId, 0, 20) })
      queryClient.invalidateQueries({ queryKey: runKeys.recent(0, 20) })
    },
  })
}

export function useTaskRuns(taskId: number, skip: number = 0, limit: number = 20, status?: string) {
  return useQuery({
    queryKey: runKeys.list(taskId, skip, limit, status),
    queryFn: () => apiClient.getTaskRuns(taskId, skip, limit, status),
    enabled: taskId > 0,
    staleTime: 15000, // 15 seconds for real-time feel
  })
}

export function useTaskRun(taskId: number, runId: number) {
  return useQuery({
    queryKey: runKeys.detail(taskId, runId),
    queryFn: () => apiClient.getTaskRun(taskId, runId),
    enabled: taskId > 0 && runId > 0,
    staleTime: 10000,
  })
}

export function useRun(runId: number) {
  return useQuery({
    queryKey: runKeys.detailById(runId),
    queryFn: () => apiClient.getRun(runId),
    enabled: runId > 0,
    staleTime: 10000,
  })
}

export function useRecentRuns(skip: number = 0, limit: number = 20) {
  return useQuery({
    queryKey: runKeys.recent(skip, limit),
    queryFn: () => apiClient.getRecentRuns(skip, limit),
    staleTime: 15000,
  })
}
