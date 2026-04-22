import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConnections, useCreateTask, useCreateMappings } from '@/hooks/api'
import { Card, Button, Input, Steps, Select, Space, Typography, Alert, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { TaskFormData, ColumnMappingCreate, AuthType } from '@/types'
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'

const { Title, Text } = Typography
const { TextArea } = Input

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
      setFormData(prev => ({
        ...prev,
        auth_type: authData.authType,
        api_key: authData.authType === 'bearer' ? authData.bearerToken :
                 authData.authType === 'api_key' ? authData.apiKeyValue : '',
        username: authData.authType === 'basic' ? authData.username : '',
        password: authData.authType === 'basic' ? authData.password : '',
        oauth_config: authData.authType === 'oauth' ? (() => { try { return JSON.parse(authData.oauthConfig) } catch { return null } })() : null,
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

    const finalData: TaskFormData = { ...formData, headers_json: headerObj, body_json: bodyObj }
    if (!finalData.name.trim()) { message.warning('Task name is required'); return }
    if (!finalData.endpoint_path.trim()) { message.warning('Endpoint URL is required'); return }
    if (!finalData.dest_table.trim()) { message.warning('Table name is required'); return }
    if (!finalData.connection_id) { message.warning('Destination connection is required'); return }

    try {
      const createdTask = await createTaskMutation.mutateAsync(finalData as any)
      if (mappings.length > 0 && !skipMappings) {
        try {
          await createMappingsMutation.mutateAsync({ taskId: createdTask.id, mappings })
        } catch (mappingErr) {
          console.error('Failed to create mappings:', mappingErr)
        }
      }
      message.success('Task created successfully!')
      navigate('/tasks')
    } catch {
      message.error('Failed to create task')
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
                onChange={(value) => setAuthData({ authType: value as AuthType, bearerToken: '', apiKeyHeaderName: 'X-API-Key', apiKeyValue: '', username: '', password: '', oauthConfig: '{}' })}
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
              <div>
                <Text strong>OAuth Configuration (JSON)</Text>
                <TextArea
                  value={authData.oauthConfig}
                  onChange={(e) => setAuthData({ ...authData, oauthConfig: e.target.value })}
                  placeholder='{"token_url": "https://...", "client_id": "...", "client_secret": "..."}'
                  rows={4}
                  style={{ fontFamily: 'monospace' }}
                />
              </div>
            )}

            {authData.authType === 'none' && (
              <Alert message="No authentication will be used for API requests" type="info" showIcon />
            )}
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
