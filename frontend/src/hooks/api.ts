import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import {
  TaskCreate,
  TaskUpdate,
  ColumnMappingCreate,
  ColumnMappingUpdate,
  MappingTemplate,
  TaskSchedule,
  ScheduleCreate,
  ScheduleUpdate,
  Connection,
  ConnectionCreate,
  ConnectionUpdate,
  ConnectionTestRequest,
} from '@/types'

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

export const mappingKeys = {
  all: ['mappings'] as const,
  lists: () => [...mappingKeys.all, 'list'] as const,
  list: (taskId: number, skip: number, limit: number, activeOnly?: boolean) =>
    [...mappingKeys.lists(), { taskId, skip, limit, activeOnly }] as const,
  details: () => [...mappingKeys.all, 'detail'] as const,
  detail: (id: number) => [...mappingKeys.details(), id] as const,
  preview: (taskId: number) => [...mappingKeys.all, 'preview', taskId] as const,
  columns: (tableName: string, connectionId: string) =>
    [...mappingKeys.all, 'columns', { tableName, connectionId }] as const,
  suggestions: (sourceType: string, destType: string) => 
    [...mappingKeys.all, 'suggestions', sourceType, destType] as const,
}

export const scheduleKeys = {
  all: ['schedules'] as const,
  lists: () => [...scheduleKeys.all, 'list'] as const,
  list: (skip: number, limit: number, isActive?: boolean) =>
    [...scheduleKeys.lists(), { skip, limit, isActive }] as const,
  details: () => [...scheduleKeys.all, 'detail'] as const,
  detail: (taskId: number) => [...scheduleKeys.details(), { taskId }] as const,
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

// Column Mapping hooks

/**
 * Fetch all mappings for a task with optional filtering
 */
export function useColumnMappings(taskId: number, skip: number = 0, limit: number = 50, activeOnly?: boolean) {
  return useQuery({
    queryKey: mappingKeys.list(taskId, skip, limit, activeOnly),
    queryFn: () => apiClient.getColumnMappings(taskId, skip, limit, activeOnly),
    enabled: taskId > 0,
    staleTime: 30000,
  })
}

/**
 * Create multiple column mappings for a task
 */
export function useCreateMappings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, mappings }: { taskId: number; mappings: ColumnMappingCreate[] }) =>
      apiClient.createColumnMappings(taskId, mappings),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: mappingKeys.lists() })
      queryClient.invalidateQueries({ queryKey: mappingKeys.list(taskId, 0, 50) })
    },
  })
}

/**
 * Update a single column mapping
 */
export function useUpdateMapping() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ColumnMappingUpdate }) =>
      apiClient.updateColumnMapping(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mappingKeys.lists() })
    },
  })
}

/**
 * Delete a column mapping
 */
export function useDeleteMapping() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiClient.deleteColumnMapping(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mappingKeys.lists() })
    },
  })
}

/**
 * Fetch preview of available fields from API response for mapping configuration
 * Supports both manual JSON paste and auto-fetch modes
 */
export function usePreviewFields(taskId: number, sampleJson?: string) {
  return useQuery({
    queryKey: mappingKeys.preview(taskId),
    queryFn: () => apiClient.previewMappingFields(taskId, sampleJson),
    enabled: taskId > 0,
    staleTime: 0, // Never cache - always fresh when component mounts
  })
}

/**
 * Fetch preview of available fields (standalone - for wizard without task ID)
 * Supports both manual JSON paste and auto-fetch modes
 */
export function usePreviewFieldsStandalone(params: {
  sample_json?: string
  use_auto_fetch?: boolean
  method?: string
  url?: string
  headers?: Record<string, string>
  params?: Record<string, any>
  json_body?: Record<string, any>
  record_path?: string
}) {
  return useMutation({
    mutationFn: () => apiClient.previewMappingFieldsStandalone(params),
  })
}

/**
 * Fetch Oracle column metadata for a table
 * Used to show available destination columns and their types
 */
export function useOracleColumns(tableName: string, connectionId?: string) {
  return useQuery({
    queryKey: mappingKeys.columns(tableName, connectionId || ''),
    queryFn: () => apiClient.getOracleColumns(tableName, connectionId as string),
    enabled: tableName.length > 0 && !!connectionId,
    staleTime: 60000, // 1 minute
  })
}

/**
 * Get transform recommendations based on source and destination field types
 * Shows auto-suggest badges in the mapping UI
 */
export function useSuggestTransforms(sourceType: string, destType: string) {
  return useQuery({
    queryKey: mappingKeys.suggestions(sourceType, destType),
    queryFn: () => apiClient.suggestTransforms(sourceType, destType),
    enabled: sourceType.length > 0 && destType.length > 0,
    staleTime: 86400000, // 24 hours - type combinations don't change
  })
}

/**
 * Template management hooks for localStorage
 */
export function useSaveMappingTemplate(onSuccess?: () => void) {
  return useMutation({
    mutationFn: (template: MappingTemplate) => {
      // Save to localStorage
      const templates = JSON.parse(localStorage.getItem('mapping_templates') || '[]')
      templates.push(template)
      localStorage.setItem('mapping_templates', JSON.stringify(templates))
      return Promise.resolve(template)
    },
    onSuccess,
  })
}

export function useLoadMappingTemplates() {
  return useQuery({
    queryKey: ['mapping_templates'],
    queryFn: () => {
      const templates = JSON.parse(localStorage.getItem('mapping_templates') || '[]')
      return templates as MappingTemplate[]
    },
    staleTime: Infinity, // localStorage data doesn't stale
  })
}

export function useDeleteMappingTemplate(onSuccess?: () => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (templateName: string) => {
      const templates = JSON.parse(localStorage.getItem('mapping_templates') || '[]')
      const filtered = templates.filter((t: MappingTemplate) => t.name !== templateName)
      localStorage.setItem('mapping_templates', JSON.stringify(filtered))
      return Promise.resolve()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping_templates'] })
      onSuccess?.()
    },
  })
}

// Schedule hooks
export function useSchedule(taskId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: scheduleKeys.detail(taskId),
    queryFn: () => apiClient.getSchedule(taskId),
    enabled: enabled && taskId > 0,
  })
}

export function useListSchedules(skip: number = 0, limit: number = 10, isActive?: boolean) {
  return useQuery({
    queryKey: scheduleKeys.list(skip, limit, isActive),
    queryFn: () => apiClient.listSchedules(skip, limit, isActive),
  })
}

export function useCreateSchedule(onSuccess?: (schedule: TaskSchedule) => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: number; data: ScheduleCreate }) =>
      apiClient.createSchedule(taskId, data),
    onSuccess: (schedule, { taskId }) => {
      // Invalidate both the specific schedule and the list
      queryClient.invalidateQueries({ queryKey: scheduleKeys.detail(taskId) })
      queryClient.invalidateQueries({ queryKey: scheduleKeys.lists() })
      onSuccess?.(schedule)
    },
  })
}

export function useUpdateSchedule(onSuccess?: (schedule: TaskSchedule) => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ scheduleId, data }: { scheduleId: number; data: ScheduleUpdate }) =>
      apiClient.updateSchedule(scheduleId, data),
    onSuccess: (schedule) => {
      // Invalidate the lists since schedule details changed
      queryClient.invalidateQueries({ queryKey: scheduleKeys.lists() })
      onSuccess?.(schedule)
    },
  })
}

export function useDeleteSchedule(onSuccess?: () => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scheduleId: number) => apiClient.deleteSchedule(scheduleId),
    onSuccess: () => {
      // Invalidate all schedule queries
      queryClient.invalidateQueries({ queryKey: scheduleKeys.all })
      onSuccess?.()
    },
  })
}

export function useResumeSchedule(onSuccess?: () => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scheduleId: number) => apiClient.resumeSchedule(scheduleId),
    onSuccess: () => {
      // Invalidate all schedule queries
      queryClient.invalidateQueries({ queryKey: scheduleKeys.all })
      onSuccess?.()
    },
  })
}

// Connection query keys
export const connectionKeys = {
  all: ['connections'] as const,
  lists: () => [...connectionKeys.all, 'list'] as const,
  detail: (id: string) => [...connectionKeys.all, 'detail', id] as const,
}

// Connection hooks
export function useConnections() {
  return useQuery({
    queryKey: connectionKeys.lists(),
    queryFn: () => apiClient.getConnections(),
    staleTime: 30000, // 30 seconds
  })
}

export function useConnection(id: string) {
  return useQuery({
    queryKey: connectionKeys.detail(id),
    queryFn: () => apiClient.getConnection(id),
    enabled: id.length > 0,
    staleTime: 30000,
  })
}

export function useCreateConnection(onSuccess?: (conn: Connection) => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ConnectionCreate) => apiClient.createConnection(data),
    onSuccess: (conn) => {
      queryClient.invalidateQueries({ queryKey: connectionKeys.lists() })
      onSuccess?.(conn)
    },
  })
}

export function useUpdateConnection(onSuccess?: (conn: Connection) => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ConnectionUpdate }) =>
      apiClient.updateConnection(id, data),
    onSuccess: (conn) => {
      queryClient.invalidateQueries({ queryKey: connectionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: connectionKeys.detail(conn.id) })
      onSuccess?.(conn)
    },
  })
}

export function useDeleteConnection(onSuccess?: () => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.deleteConnection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: connectionKeys.lists() })
      onSuccess?.()
    },
  })
}

export function useTestConnection() {
  return useMutation({
    mutationFn: (data: ConnectionTestRequest) => apiClient.testConnection(data),
  })
}
