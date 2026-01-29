// Task types
export interface Task {
  id: number
  name: string
  description?: string
  http_method: string
  endpoint_path: string
  query_params_json?: Record<string, any>
  headers_json?: Record<string, any>
  body_json?: Record<string, any>
  record_path?: string
  dest_table: string
  batch_size: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface TaskCreate extends Omit<Task, 'id'> {}
export interface TaskUpdate extends Partial<Omit<Task, 'id'>> {}

// Task Run types
export interface TaskRun {
  id: number
  task_id: number
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED'
  rows_fetched: number
  rows_inserted: number
  error_count: number
  warning_count?: number
  started_at: string
  ended_at?: string
  execution_logs?: TaskLog[]
  row_errors?: TaskRunLog[]
}

export interface TaskLog {
  id: number
  task_id: number
  run_id: number
  step_name: string
  status: string
  message: string
  details?: Record<string, any>
  created_at: string
}

export interface TaskRunLog {
  id: number
  task_id: number
  run_id: number
  row_index: number
  row_data: Record<string, any>
  errors: Array<{ column: string; error_type: string; message: string }>
  created_at: string
}

// Task Stats types
export interface TaskStats {
  task_id: number
  total_runs: number
  successful_runs: number
  failed_runs: number
  success_rate: number
  total_rows_fetched: number
  total_rows_inserted: number
  total_errors: number
  avg_duration_seconds: number
  last_run_at?: string
  last_run_status?: string
}

// API Response types
export interface ApiResponse<T> {
  data: T
  status: number
}

export interface ApiListResponse<T> {
  data: T[]
  total: number
  skip: number
  limit: number
}

// Form types
export interface TaskFormData {
  name: string
  description?: string
  http_method: 'GET' | 'POST' | 'PUT' | 'PATCH'
  endpoint_path: string
  query_params_json?: Record<string, any>
  headers_json?: Record<string, any>
  body_json?: Record<string, any>
  record_path?: string
  dest_table: string
  batch_size?: number
  is_active?: boolean
}
