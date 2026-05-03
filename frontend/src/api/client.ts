import axios, { AxiosInstance } from 'axios'
import {
  Task,
  TaskRun,
  TaskStats,
  TaskCreate,
  TaskUpdate,
  ColumnMapping,
  ColumnMappingCreate,
  ColumnMappingUpdate,
  MappingPreview,
  OracleColumnsResponse,
  TransformSuggestionsResponse,
  TaskSchedule,
  ScheduleCreate,
  ScheduleUpdate,
  ScheduleListResponse,
  Connection,
  ConnectionCreate,
  ConnectionUpdate,
  ConnectionTestRequest,
  ConnectionTestResult,
  ConnectionListResponse,
  BackfillResponse,
  ReplayResponse,
} from '@/types'

const API_BASE_URL = '/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // Task endpoints
  async createTask(data: TaskCreate): Promise<Task> {
    const response = await this.client.post('/tasks/', data)
    return response.data
  }

  async getTasks(skip: number = 0, limit: number = 10, isActive?: boolean): Promise<Task[]> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    if (isActive !== undefined) {
      params.append('is_active', isActive.toString())
    }
    const response = await this.client.get(`/tasks/?${params}`)
    return response.data
  }

  async getTask(id: number): Promise<Task> {
    const response = await this.client.get(`/tasks/${id}`)
    return response.data
  }

  async updateTask(id: number, data: TaskUpdate): Promise<Task> {
    const response = await this.client.put(`/tasks/${id}`, data)
    return response.data
  }

  async deleteTask(id: number): Promise<void> {
    await this.client.delete(`/tasks/${id}`)
  }

  // Task Stats
  async getTaskStats(id: number): Promise<TaskStats> {
    const response = await this.client.get(`/tasks/${id}/stats`)
    return response.data
  }

  // Task Run endpoints
  async triggerRun(taskId: number): Promise<{ status: string; run_id: number; task_id: number }> {
    const response = await this.client.post(`/tasks/${taskId}/run`)
    return response.data
  }

  async getTaskRuns(taskId: number, skip: number = 0, limit: number = 20, status?: string): Promise<TaskRun[]> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    if (status) {
      params.append('status', status)
    }
    const response = await this.client.get(`/tasks/${taskId}/runs?${params}`)
    return response.data
  }

  async getTaskRun(taskId: number, runId: number): Promise<TaskRun> {
    const response = await this.client.get(`/tasks/${taskId}/runs/${runId}`)
    return response.data
  }

  async getRun(runId: number): Promise<TaskRun> {
    const response = await this.client.get(`/runs/${runId}`)
    return response.data
  }

  // Backfill / replay (P0-C)
  async triggerBackfill(
    taskId: number,
    cursorStart: string,
    cursorEnd?: string,
  ): Promise<BackfillResponse> {
    const response = await this.client.post(`/tasks/${taskId}/backfill`, {
      cursor_start: cursorStart,
      cursor_end: cursorEnd,
    })
    return response.data
  }

  async replayRun(runId: number, force: boolean = false): Promise<ReplayResponse> {
    const response = await this.client.post(`/runs/${runId}/replay`, { force })
    return response.data
  }

  async getRecentRuns(skip: number = 0, limit: number = 20): Promise<TaskRun[]> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    const response = await this.client.get(`/runs?${params}`)
    return response.data
  }

  // Column Mapping endpoints
  async getColumnMappings(
    taskId: number,
    skip: number = 0,
    limit: number = 50,
    activeOnly?: boolean
  ): Promise<ColumnMapping[]> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    if (activeOnly !== undefined) {
      params.append('is_active', activeOnly.toString())
    }
    const response = await this.client.get(`/tasks/${taskId}/mappings?${params}`)
    return response.data
  }

  async createColumnMappings(taskId: number, mappings: ColumnMappingCreate[]): Promise<ColumnMapping[]> {
    const response = await this.client.post(`/tasks/${taskId}/mappings`, { mappings })
    return response.data
  }

  async updateColumnMapping(id: number, data: ColumnMappingUpdate): Promise<ColumnMapping> {
    const response = await this.client.put(`/mappings/${id}`, data)
    return response.data
  }

  async deleteColumnMapping(id: number): Promise<void> {
    await this.client.delete(`/mappings/${id}`)
  }

  // Preview fields from API response
  async previewMappingFields(taskId: number, sampleJson?: string): Promise<MappingPreview> {
    const response = await this.client.post(`/tasks/${taskId}/preview-fields`, {
      sample_json: sampleJson,
    })
    return response.data
  }

  // Preview fields standalone (for wizard without task ID)
  async previewMappingFieldsStandalone(params: {
    sample_json?: any
    use_auto_fetch?: boolean
    method?: string
    url?: string
    headers?: Record<string, string>
    params?: Record<string, any>
    json_body?: Record<string, any>
    record_path?: string
    auth_type?: string
    api_key?: string
    username?: string
    password?: string
    oauth_config?: Record<string, any>
  }): Promise<MappingPreview> {
    const requestBody = {
      use_auto_fetch: params.use_auto_fetch ?? false,
      sample_json: params.sample_json,
      method: params.method ?? 'GET',
      url: params.url,
      headers: params.headers,
      params: params.params,
      json_body: params.json_body,
      record_path: params.record_path,
      auth_type: params.auth_type,
      api_key: params.api_key,
      username: params.username,
      password: params.password,
      oauth_config: params.oauth_config,
    }

    const response = await this.client.post('/preview-fields-standalone', requestBody)
    return response.data
  }

  // Get Oracle table columns metadata
  async getOracleColumns(tableName: string, connectionId: string): Promise<OracleColumnsResponse> {
    const params = new URLSearchParams({ connection_id: connectionId })
    const response = await this.client.get(`/oracle/tables/${tableName}/columns?${params}`)
    return response.data
  }

  // Get transform suggestions based on type mismatch
  async suggestTransforms(sourceType: string, destType: string): Promise<TransformSuggestionsResponse> {
    const params = new URLSearchParams({
      source_type: sourceType,
      dest_type: destType,
    })
    const response = await this.client.post(`/tasks/suggest-transforms?${params}`)
    return response.data
  }

  // Health check
  async getHealth(): Promise<{ status: string; env: string }> {
    const response = await this.client.get('/health')
    return response.data
  }

  // Schedule endpoints
  async createSchedule(taskId: number, data: ScheduleCreate): Promise<TaskSchedule> {
    const response = await this.client.post(`/tasks/${taskId}/schedule`, data)
    return response.data
  }

  async getSchedule(taskId: number): Promise<TaskSchedule> {
    const response = await this.client.get(`/tasks/${taskId}/schedule`)
    return response.data
  }

  async updateSchedule(scheduleId: number, data: ScheduleUpdate): Promise<TaskSchedule> {
    const response = await this.client.put(`/schedules/${scheduleId}`, data)
    return response.data
  }

  async deleteSchedule(scheduleId: number): Promise<void> {
    await this.client.delete(`/schedules/${scheduleId}`)
  }

  async listSchedules(skip: number = 0, limit: number = 10, isActive?: boolean): Promise<ScheduleListResponse> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    if (isActive !== undefined) {
      params.append('is_active', isActive.toString())
    }
    const response = await this.client.get(`/schedules/?${params}`)
    return response.data
  }

  async resumeSchedule(scheduleId: number): Promise<{ message: string }> {
    const response = await this.client.post(`/schedules/${scheduleId}/resume`)
    return response.data
  }

  // Database Connection endpoints
  async getConnections(): Promise<ConnectionListResponse> {
    const response = await this.client.get('/connections/')
    return response.data
  }

  async getConnection(id: string): Promise<Connection> {
    const response = await this.client.get(`/connections/${id}`)
    return response.data
  }

  async createConnection(data: ConnectionCreate): Promise<Connection> {
    const response = await this.client.post('/connections/', data)
    return response.data
  }

  async updateConnection(id: string, data: ConnectionUpdate): Promise<Connection> {
    const response = await this.client.put(`/connections/${id}`, data)
    return response.data
  }

  async deleteConnection(id: string): Promise<void> {
    await this.client.delete(`/connections/${id}`)
  }

  async testConnection(data: ConnectionTestRequest): Promise<ConnectionTestResult> {
    const response = await this.client.post('/connections/test', data)
    return response.data
  }
}

export const apiClient = new ApiClient()
