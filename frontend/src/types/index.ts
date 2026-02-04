// Authentication types
export type AuthType = 'none' | 'bearer' | 'api_key' | 'basic' | 'oauth'

export interface TaskAuth {
  auth_type: AuthType
  username?: string
  // api_key and password excluded from responses for security
}

// Upsert configuration types (Phase 8)
export interface UpsertConfig {
  upsert_enabled: boolean
  upsert_keys?: string[]  // Column names for matching
  skip_column?: string    // Column to check for skip condition
  skip_value?: string     // Value that triggers skip (e.g., 'Y')
  continue_on_error: boolean
}

// Task types
export interface Task extends TaskAuth, UpsertConfig {
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

export interface TaskCreateAuth {
  auth_type?: AuthType
  api_key?: string
  username?: string
  password?: string
  oauth_config?: Record<string, any>
}

export interface TaskCreate extends Omit<Task, 'id'>, TaskCreateAuth {}
export interface TaskUpdate extends Partial<Omit<Task, 'id'>> {}

// Column Mapping types
export interface ColumnMapping {
  id: number
  task_id: number
  source_field: string // Flattened field from API response (e.g., "user.address.city")
  dest_column: string  // Target Oracle column name
  transform_rules?: string // JSON string of transforms to apply
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ColumnMappingCreate {
  source_field: string
  dest_column: string
  transform_rules?: string | Record<string, any>
  is_active?: boolean
}

export interface ColumnMappingUpdate extends Partial<ColumnMappingCreate> {}

// Field preview types for mapping configuration
export interface FieldPreview {
  field_name: string       // Full flattened path (e.g., "user.address.city")
  field_type: 'string' | 'number' | 'boolean' | 'null' | 'array' | 'object'
  sample_value: any        // Example value from API response
  nullable: boolean        // Whether field can be null
  parent_path?: string     // Parent path for tree hierarchy (e.g., "user.address")
}

export interface MappingPreview {
  fields: FieldPreview[]
  total_fields: number
  flattened_successfully: boolean
  errors?: string[]
}

// Oracle column metadata
export interface OracleColumn {
  column_name: string
  data_type: string       // Oracle type (VARCHAR2, NUMBER, DATE, TIMESTAMP, etc.)
  nullable: string        // 'Y' or 'N'
  max_length?: number     // For VARCHAR2, CHAR types
}

export interface OracleColumnsResponse {
  table_name: string
  columns: OracleColumn[]
  total_columns: number
}

// Transform suggestion types
export interface TransformSuggestion {
  transform_name: string
  description: string
  confidence: 'high' | 'medium' | 'low'
  reason: string          // Why this transform is suggested
}

export interface TransformSuggestionsResponse {
  source_type: string
  dest_type: string
  suggestions: TransformSuggestion[]
  requires_transform: boolean    // Whether a transform is required
  warning_message?: string       // Warning if types are incompatible
}

// Mapping template for save/load in localStorage
export interface MappingTemplate {
  name: string
  description?: string
  mappings: ColumnMappingCreate[]
  created_at: string
  updated_at: string
}

// Task Run types
export interface TaskRun {
  id: number
  task_id: number
  task_name?: string
  is_retry?: boolean
  retry_of_run_id?: number
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED'
  rows_fetched: number
  rows_inserted: number
  rows_updated?: number   // Phase 8: Upsert updates
  rows_skipped?: number   // Phase 8: Skipped due to skip condition
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
  total_rows_updated?: number  // Phase 8: Upsert updates
  total_rows_skipped?: number  // Phase 8: Skipped rows
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
  // Auth fields
  auth_type?: AuthType
  api_key?: string
  username?: string
  password?: string
  oauth_config?: Record<string, any>
  // Upsert fields (Phase 8)
  upsert_enabled?: boolean
  upsert_keys?: string[]
  skip_column?: string
  skip_value?: string
  continue_on_error?: boolean
}

// Schedule types
export interface TaskSchedule {
  id: number
  task_id: number
  cron_expression: string
  is_active: boolean
  last_run_date?: string
  next_run_date?: string
  created_at: string
}

export interface TaskScheduleWithTaskName extends TaskSchedule {
  task_name: string
}

export interface ScheduleCreate {
  cron_expression: string
  is_active?: boolean
}

export interface ScheduleUpdate extends Partial<ScheduleCreate> {}

export interface ScheduleListResponse {
  total_count: number
  skip: number
  limit: number
  schedules: TaskScheduleWithTaskName[]
}
