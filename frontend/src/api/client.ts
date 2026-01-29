import axios, { AxiosInstance } from 'axios'
import { Task, TaskRun, TaskStats, TaskCreate, TaskUpdate } from '@/types'

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

  async getRecentRuns(skip: number = 0, limit: number = 20): Promise<TaskRun[]> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    const response = await this.client.get(`/runs?${params}`)
    return response.data
  }

  // Health check
  async getHealth(): Promise<{ status: string; env: string }> {
    const response = await this.client.get('/health')
    return response.data
  }
}

export const apiClient = new ApiClient()
