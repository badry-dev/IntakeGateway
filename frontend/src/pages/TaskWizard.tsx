import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConnections, useCreateTask, useCreateMappings } from '@/hooks/api'
import { Card, Button, Input, Steps, Select, Space, Typography, Alert, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { TaskFormData, ColumnMappingCreate, AuthType } from '@/types'
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'

const { Title, Text } = Typography
const { TextArea } = Input

const getApiErrorMessage = (err: unknown, fallback: string) => {
  const apiError = err as { response?: { data?: { detail?: unknown } } }
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  if (err instanceof Error) return err.message
  return fallback
}

const STEPS = [
  { title: 'Basic Info', description: 'Task name and description' },
  { title: 'Endpoint', description: 'API endpoint configuration' },
  { title: 'Headers & Body', description: 'Request headers and payload' },
  { title: 'Authentication', description: 'API authentication method' },
  { title: 'Mapping', description: 'Column mapping configuration' },
  { title: 'Review', description: 'Review and create' },
]

export function TaskWizard() {
  const navigate = useNavigate()
  const { data: connectionsData } = useConnections()
  const createTaskMutation = useCreateTask()
  const createMappingsMutation = useCreateMappings()
  const [currentStep, setCurrentStep] = useState(0)
  const [formData, setFormData] = useState<TaskFormData>({
    name: '',
    description: '',
    connection_id: '',
    endpoint_path: '',
    http_method: 'GET',
    dest_table: '',
    headers_json: {},
    body_json: {},
    batch_size: 500,
    is_active: true,
    auth_type: 'none',
  })

  const [headers, setHeaders] = useState<{ key: string; value: string }[]>([{ key: '', value: '' }])
  const [authData, setAuthData] = useState({
    authType: 'none' as AuthType,
    bearerToken: '',
    apiKeyHeaderName: 'X-API-Key',
    apiKeyValue: '',
    username: '',
    password: '',
    oauthConfig: '{}',
    // Structured OAuth fields (P0-A). Server encrypts client_secret/access_token/refresh_token at rest.
    oauthGrantType: 'static' as 'static' | 'client_credentials' | 'refresh_token',
    oauthTokenUrl: '',
    oauthClientId: '',
    oauthClientSecret: '',
    oauthScope: '',
    oauthAudience: '',
    oauthAccessToken: '',
    oauthRefreshToken: '',
  })
  // Advanced settings (rate-limit + cursor) shown in step 1 collapsible.
  const [rateLimit, setRateLimit] = useState({
    maxRetries: '' as string,
    maxWaitSeconds: '' as string,
    rps: '' as string,
  })
  const [cursorCfg, setCursorCfg] = useState({
    field: '',
    paramName: '',
    initialValue: '',
  })
  const [bodyJson, setBodyJson] = useState('{}')
  const [mappings, setMappings] = useState<ColumnMappingCreate[]>([])
  const [skipMappings, setSkipMappings] = useState(false)

  const connections = connectionsData?.connections || []
  const selectedConnection = connections.find((connection) => connection.id === formData.connection_id)

  const goNext = () => {
    if (currentStep === 2) {
      const headerObj: Record<string, string> = {}
      headers.forEach(h => { if (h.key.trim()) headerObj[h.key] = h.value })
      setFormData(prev => ({ ...prev, headers_json: headerObj }))
      try {
        const bodyObj = bodyJson.trim() ? JSON.parse(bodyJson) : {}
        setFormData(prev => ({ ...prev, body_json: bodyObj }))
      } catch {
        message.error('Invalid JSON in request body')
        return
      }
    }
    if (currentStep === 3) {
      const buildOAuth = () => {
        if (authData.authType !== 'oauth') return undefined
        return {
          grant_type: authData.oauthGrantType,
          token_url: authData.oauthTokenUrl || undefined,
          client_id: authData.oauthClientId || undefined,
          client_secret: authData.oauthClientSecret || undefined,
          scope: authData.oauthScope || undefined,
          audience: authData.oauthAudience || undefined,
          access_token: authData.oauthAccessToken || undefined,
          refresh_token: authData.oauthRefreshToken || undefined,
        }
      }
      setFormData(prev => ({
        ...prev,
        auth_type: authData.authType,
        api_key: authData.authType === 'bearer' ? authData.bearerToken :
                 authData.authType === 'api_key' ? authData.apiKeyValue : '',
        username: authData.authType === 'basic' ? authData.username : '',
        password: authData.authType === 'basic' ? authData.password : '',
        oauth_config: authData.authType === 'api_key'
          ? { api_key_header: authData.apiKeyHeaderName }
          : undefined,
        oauth: buildOAuth(),
      }))
    }
    setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1))
  }

  const goPrev = () => setCurrentStep(prev => Math.max(prev - 1, 0))

  const handleCreate = async () => {
    const headerObj: Record<string, string> = {}
    headers.forEach(h => { if (h.key.trim()) headerObj[h.key] = h.value })
    let bodyObj = {}
    try { bodyObj = bodyJson.trim() ? JSON.parse(bodyJson) : {} } catch { message.error('Invalid JSON'); return }

    const toIntOrUndef = (v: string) => {
      if (!v.trim()) return undefined
      const n = Number(v)
      return Number.isFinite(n) ? n : undefined
    }
    const rateLimitPayload = (rateLimit.maxRetries || rateLimit.maxWaitSeconds || rateLimit.rps)
      ? {
          max_retries: toIntOrUndef(rateLimit.maxRetries),
          max_wait_seconds: toIntOrUndef(rateLimit.maxWaitSeconds),
          rps: toIntOrUndef(rateLimit.rps),
        }
      : undefined
    const cursorPayload = (cursorCfg.field || cursorCfg.paramName || cursorCfg.initialValue)
      ? {
          field: cursorCfg.field || undefined,
          param_name: cursorCfg.paramName || undefined,
          initial_value: cursorCfg.initialValue || undefined,
        }
      : undefined

    const finalData: TaskFormData = {
      ...formData,
      headers_json: headerObj,
      body_json: bodyObj,
      ...(rateLimitPayload ? { rate_limit: rateLimitPayload } : {}),
      ...(cursorPayload ? { cursor: cursorPayload } : {}),
    }
    if (!finalData.name.trim()) { message.warning('Task name is required'); return }
    if (!finalData.endpoint_path.trim()) { message.warning('Endpoint URL is required'); return }
    if (!finalData.dest_table.trim()) { message.warning('Table name is required'); return }
    if (!finalData.connection_id) { message.warning('Destination connection is required'); return }

    try {
      const createdTask = await createTaskMutation.mutateAsync(finalData)
      if (mappings.length > 0 && !skipMappings) {
        try {
          await createMappingsMutation.mutateAsync({ taskId: createdTask.id, mappings })
        } catch (mappingErr) {
          console.error('Failed to create mappings:', mappingErr)
          message.error(
            `Task was created, but saving column mappings failed: ${getApiErrorMessage(mappingErr, 'Unknown error')}`
          )
          return
        }
      }
      message.success('Task created successfully!')
      navigate('/tasks')
    } catch (err) {
      message.error(`Failed to create task: ${getApiErrorMessage(err, 'Unknown error')}`)
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 0: return !!(formData.name.trim() && formData.dest_table.trim() && formData.connection_id)
      case 1: return !!formData.endpoint_path.trim()
      case 2: return true
      case 3:
        if (authData.authType === 'bearer') return !!authData.bearerToken.trim()
        if (authData.authType === 'api_key') return !!(authData.apiKeyHeaderName.trim() && authData.apiKeyValue.trim())
        if (authData.authType === 'basic') return !!(authData.username.trim() && authData.password.trim())
        if (authData.authType === 'oauth') {
          // Per-grant required fields. Mirrors backend OAuthConfigIn validator.
          if (authData.oauthGrantType === 'static') {
            return !!authData.oauthAccessToken.trim()
          }
          const commonOauthOk =
            !!authData.oauthTokenUrl.trim() &&
            !!authData.oauthClientId.trim() &&
            !!authData.oauthClientSecret.trim()
          if (authData.oauthGrantType === 'client_credentials') {
            return commonOauthOk
          }
          if (authData.oauthGrantType === 'refresh_token') {
            return commonOauthOk && !!authData.oauthRefreshToken.trim()
          }
          return false
        }
        return true
      case 4: return mappings.length > 0 || skipMappings
      case 5: return true
      default: return false
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 900 }}>
      <Space>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>Back</Button>
        <Title level={3} style={{ margin: 0 }}>Create New Task</Title>
      </Space>

      <Card>
        <Steps current={currentStep} size="small" items={STEPS} style={{ marginBottom: 32 }} />

        {/* Basic Info */}
        {currentStep === 0 && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>Task Name *</Text>
              <Input
                placeholder="e.g., Sync Users, Import Products"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div>
              <Text strong>Description</Text>
              <Input
                placeholder="Describe what this task does"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
            <div>
              <Text strong>Table Name *</Text>
              <Input
                placeholder="e.g., users, products"
                value={formData.dest_table}
                onChange={(e) => setFormData({ ...formData, dest_table: e.target.value })}
              />
            </div>
            <div>
              <Text strong>Destination Connection *</Text>
              <Select
                placeholder={connections.length > 0 ? 'Select destination connection' : 'Create a connection in Settings first'}
                value={formData.connection_id}
                onChange={(value) => setFormData({ ...formData, connection_id: value })}
                options={connections.map((connection) => ({
                  value: connection.id,
                  label: `${connection.name} (${connection.db_type})`,
                }))}
                style={{ width: '100%' }}
                disabled={connections.length === 0}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                Every task must target one saved destination connection.
              </Text>
            </div>
            {connections.length === 0 && (
              <Alert
                message="Connection required"
                description="Create a connection in Settings before creating tasks. This flow no longer uses a default or fallback database."
                type="warning"
                showIcon
              />
            )}
          </Space>
        )}

        {/* Endpoint */}
        {currentStep === 1 && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>Endpoint URL *</Text>
              <Input
                placeholder="https://api.example.com/users"
                value={formData.endpoint_path}
                onChange={(e) => setFormData({ ...formData, endpoint_path: e.target.value })}
              />
            </div>
            <div>
              <Text strong>HTTP Method *</Text>
              <Select
                value={formData.http_method}
                onChange={(value) => setFormData({ ...formData, http_method: value })}
                options={[
                  { value: 'GET', label: 'GET' },
                  { value: 'POST', label: 'POST' },
                  { value: 'PUT', label: 'PUT' },
                  { value: 'PATCH', label: 'PATCH' },
                ]}
                style={{ width: '100%' }}
              />
            </div>
            <Alert
              message="Tip"
              description="Make sure the endpoint returns data in a format compatible with your target table structure."
              type="info"
              showIcon
            />
          </Space>
        )}

        {/* Headers & Body */}
        {currentStep === 2 && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>Request Headers</Text>
              {headers.map((header, idx) => (
                <Space key={idx} style={{ display: 'flex', marginBottom: 8 }}>
                  <Input
                    placeholder="Header name"
                    value={header.key}
                    onChange={(e) => { const n = [...headers]; n[idx].key = e.target.value; setHeaders(n) }}
                    style={{ flex: 1 }}
                  />
                  <Input
                    placeholder="Header value"
                    value={header.value}
                    onChange={(e) => { const n = [...headers]; n[idx].value = e.target.value; setHeaders(n) }}
                    style={{ flex: 1 }}
                  />
                  {headers.length > 1 && (
                    <Button onClick={() => setHeaders(headers.filter((_, i) => i !== idx))}>Remove</Button>
                  )}
                </Space>
              ))}
              <Button type="dashed" onClick={() => setHeaders([...headers, { key: '', value: '' }])} block>
                + Add Header
              </Button>
            </div>
            <div>
              <Text strong>Request Body (JSON)</Text>
              <TextArea
                value={bodyJson}
                onChange={(e) => setBodyJson(e.target.value)}
                placeholder="{}"
                rows={6}
                style={{ fontFamily: 'monospace' }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>Enter valid JSON or leave empty for GET requests</Text>
            </div>
          </Space>
        )}

        {/* Authentication */}
        {currentStep === 3 && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>Authentication Type</Text>
              <Select
                value={authData.authType}
                onChange={(value) => setAuthData({
                  authType: value as AuthType,
                  bearerToken: '',
                  apiKeyHeaderName: 'X-API-Key',
                  apiKeyValue: '',
                  username: '',
                  password: '',
                  oauthConfig: '{}',
                  oauthGrantType: 'static',
                  oauthTokenUrl: '',
                  oauthClientId: '',
                  oauthClientSecret: '',
                  oauthScope: '',
                  oauthAudience: '',
                  oauthAccessToken: '',
                  oauthRefreshToken: '',
                })}
                options={[
                  { value: 'none', label: 'No Authentication' },
                  { value: 'bearer', label: 'Bearer Token' },
                  { value: 'api_key', label: 'API Key' },
                  { value: 'basic', label: 'Basic Auth' },
                  { value: 'oauth', label: 'OAuth 2.0' },
                ]}
                style={{ width: '100%' }}
              />
            </div>

            {authData.authType === 'bearer' && (
              <div>
                <Text strong>Bearer Token</Text>
                <Input.Password
                  placeholder="Enter your bearer token"
                  value={authData.bearerToken}
                  onChange={(e) => setAuthData({ ...authData, bearerToken: e.target.value })}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Will be sent as: Authorization: Bearer {authData.bearerToken || '[token]'}
                </Text>
              </div>
            )}

            {authData.authType === 'api_key' && (
              <>
                <div>
                  <Text strong>Header Name</Text>
                  <Input
                    placeholder="e.g., X-API-Key"
                    value={authData.apiKeyHeaderName}
                    onChange={(e) => setAuthData({ ...authData, apiKeyHeaderName: e.target.value })}
                  />
                </div>
                <div>
                  <Text strong>API Key Value</Text>
                  <Input.Password
                    placeholder="Enter your API key"
                    value={authData.apiKeyValue}
                    onChange={(e) => setAuthData({ ...authData, apiKeyValue: e.target.value })}
                  />
                </div>
              </>
            )}

            {authData.authType === 'basic' && (
              <>
                <div>
                  <Text strong>Username</Text>
                  <Input
                    placeholder="Enter username"
                    value={authData.username}
                    onChange={(e) => setAuthData({ ...authData, username: e.target.value })}
                  />
                </div>
                <div>
                  <Text strong>Password</Text>
                  <Input.Password
                    placeholder="Enter password"
                    value={authData.password}
                    onChange={(e) => setAuthData({ ...authData, password: e.target.value })}
                  />
                </div>
              </>
            )}

            {authData.authType === 'oauth' && (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Text strong>Grant Type</Text>
                  <Select
                    value={authData.oauthGrantType}
                    onChange={(v) => setAuthData({ ...authData, oauthGrantType: v as 'static' | 'client_credentials' | 'refresh_token' })}
                    options={[
                      { value: 'static', label: 'Static (pre-issued access token)' },
                      { value: 'client_credentials', label: 'Client Credentials' },
                      { value: 'refresh_token', label: 'Refresh Token' },
                    ]}
                    style={{ width: '100%' }}
                  />
                </div>
                {authData.oauthGrantType !== 'static' && (
                  <>
                    <div>
                      <Text strong>Token URL</Text>
                      <Input
                        placeholder="https://idp.example.com/oauth/token"
                        value={authData.oauthTokenUrl}
                        onChange={(e) => setAuthData({ ...authData, oauthTokenUrl: e.target.value })}
                      />
                    </div>
                    <div>
                      <Text strong>Client ID</Text>
                      <Input
                        value={authData.oauthClientId}
                        onChange={(e) => setAuthData({ ...authData, oauthClientId: e.target.value })}
                      />
                    </div>
                    <div>
                      <Text strong>Client Secret</Text>
                      <Input.Password
                        value={authData.oauthClientSecret}
                        onChange={(e) => setAuthData({ ...authData, oauthClientSecret: e.target.value })}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Stored encrypted (Fernet) on the server. Never returned in API responses.
                      </Text>
                    </div>
                    <div>
                      <Text strong>Scope (optional)</Text>
                      <Input
                        value={authData.oauthScope}
                        onChange={(e) => setAuthData({ ...authData, oauthScope: e.target.value })}
                      />
                    </div>
                    <div>
                      <Text strong>Audience (optional)</Text>
                      <Input
                        value={authData.oauthAudience}
                        onChange={(e) => setAuthData({ ...authData, oauthAudience: e.target.value })}
                      />
                    </div>
                  </>
                )}
                {authData.oauthGrantType === 'refresh_token' && (
                  <div>
                    <Text strong>Initial Refresh Token</Text>
                    <Input.Password
                      value={authData.oauthRefreshToken}
                      onChange={(e) => setAuthData({ ...authData, oauthRefreshToken: e.target.value })}
                    />
                  </div>
                )}
                {authData.oauthGrantType === 'static' && (
                  <div>
                    <Text strong>Access Token</Text>
                    <Input.Password
                      value={authData.oauthAccessToken}
                      onChange={(e) => setAuthData({ ...authData, oauthAccessToken: e.target.value })}
                    />
                  </div>
                )}
              </Space>
            )}

            {authData.authType === 'none' && (
              <Alert message="No authentication will be used for API requests" type="info" showIcon />
            )}

            {/* Advanced (rate-limit + cursor) — optional, P0-B / P0-C */}
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: 'pointer' }}>
                <Text strong>Advanced (rate-limit & cursor)</Text>
              </summary>
              <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 12 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Rate limiting: leave blank to use server defaults
                  (HTTP_RATE_LIMIT_DEFAULT_RETRIES, HTTP_RETRY_AFTER_MAX_SECONDS).
                </Text>
                <Space size="small" style={{ width: '100%' }}>
                  <div>
                    <Text>Max 429 retries</Text>
                    <Input
                      type="number"
                      min={0}
                      max={20}
                      value={rateLimit.maxRetries}
                      onChange={(e) => setRateLimit({ ...rateLimit, maxRetries: e.target.value })}
                    />
                  </div>
                  <div>
                    <Text>Max wait (sec)</Text>
                    <Input
                      type="number"
                      min={0}
                      max={3600}
                      value={rateLimit.maxWaitSeconds}
                      onChange={(e) => setRateLimit({ ...rateLimit, maxWaitSeconds: e.target.value })}
                    />
                  </div>
                  <div>
                    <Text>Target RPS</Text>
                    <Input
                      type="number"
                      min={0}
                      max={1000}
                      value={rateLimit.rps}
                      onChange={(e) => setRateLimit({ ...rateLimit, rps: e.target.value })}
                    />
                  </div>
                </Space>
                <Text type="secondary" style={{ fontSize: 12, marginTop: 12 }}>
                  Cursor (incremental fetch): the high-water mark from successful runs is
                  stored on the task and passed as a query param on subsequent runs.
                  Identifiers must match <code>^[A-Za-z_][A-Za-z0-9_]&#123;0,99&#125;$</code>.
                </Text>
                <div>
                  <Text>Cursor field (in API response)</Text>
                  <Input
                    placeholder="e.g. updated_at"
                    value={cursorCfg.field}
                    onChange={(e) => setCursorCfg({ ...cursorCfg, field: e.target.value })}
                  />
                </div>
                <div>
                  <Text>Cursor query param name</Text>
                  <Input
                    placeholder="e.g. since"
                    value={cursorCfg.paramName}
                    onChange={(e) => setCursorCfg({ ...cursorCfg, paramName: e.target.value })}
                  />
                </div>
                <div>
                  <Text>Initial cursor value (optional)</Text>
                  <Input
                    placeholder="e.g. 2024-01-01T00:00:00Z"
                    value={cursorCfg.initialValue}
                    onChange={(e) => setCursorCfg({ ...cursorCfg, initialValue: e.target.value })}
                  />
                </div>
              </Space>
            </details>
          </Space>
        )}

        {/* Mapping */}
        {currentStep === 4 && (
          <div>
            {!formData.endpoint_path || !formData.dest_table ? (
              <Alert
                message="Configuration Required"
                description="Please complete the Endpoint and Basic Info steps first before configuring column mappings."
                type="warning"
                showIcon
              />
            ) : (
              <>
                <Alert
                  message="Column Mapping"
                  description="Configure how API response fields map to your database columns. You can fetch a sample from your API or paste JSON manually to preview available fields."
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <ColumnMappingEditor
                  wizardMode
                  taskFormData={formData}
                  existingMappings={mappings}
                  onSave={async (mappingData) => { setMappings(mappingData); setSkipMappings(false) }}
                  onFieldsLoad={() => console.log('Fields loaded')}
                />
              </>
            )}
          </div>
        )}

        {/* Review */}
        {currentStep === 5 && (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Card size="small" type="inner" title="Name"><Text>{formData.name}</Text></Card>
            <Card size="small" type="inner" title="Description"><Text>{formData.description || '(None)'}</Text></Card>
            <Card size="small" type="inner" title="Endpoint"><Text code>{formData.http_method} {formData.endpoint_path}</Text></Card>
            <Card size="small" type="inner" title="Table"><Text code>{formData.dest_table}</Text></Card>
            <Card size="small" type="inner" title="Destination Connection">
              <Text>{selectedConnection?.name || '(not selected)'}</Text>
            </Card>
            {formData.auth_type && formData.auth_type !== 'none' && (
              <Card size="small" type="inner" title="Authentication">
                <Text>Type: <Text code>{formData.auth_type}</Text></Text>
              </Card>
            )}
            {mappings.length > 0 && (
              <Card size="small" type="inner" title={`Column Mappings (${mappings.length})`}>
                {mappings.map((m, idx) => (
                  <div key={idx}><Text code>{m.source_field} → {m.dest_column}</Text></div>
                ))}
              </Card>
            )}
            {skipMappings && mappings.length === 0 && (
              <Alert
                message="No column mappings configured."
                description="You'll need to configure mappings in the Task Detail page before running this task."
                type="warning"
                showIcon
              />
            )}
          </Space>
        )}

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32 }}>
          <Button onClick={goPrev} disabled={currentStep === 0}>Previous</Button>
          {currentStep === STEPS.length - 1 ? (
            <Button type="primary" onClick={handleCreate} loading={createTaskMutation.isPending} disabled={!canProceed()}>
              Create Task
            </Button>
          ) : (
            <Button type="primary" onClick={goNext} disabled={!canProceed()}>Next</Button>
          )}
        </div>
      </Card>
    </Space>
  )
}
