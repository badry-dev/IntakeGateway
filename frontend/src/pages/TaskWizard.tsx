import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateTask, useCreateMappings, usePreviewFields, useOracleColumns } from '@/hooks/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, ChevronRight, ChevronLeft, AlertCircle } from 'lucide-react'
import { TaskFormData, ColumnMappingCreate, AuthType } from '@/types'
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

type Step = 'basic' | 'endpoint' | 'headers' | 'auth' | 'mapping' | 'review'

const STEPS: { id: Step; label: string; description: string }[] = [
  { id: 'basic', label: 'Basic Info', description: 'Task name and description' },
  { id: 'endpoint', label: 'Endpoint', description: 'API endpoint configuration' },
  { id: 'headers', label: 'Headers & Body', description: 'Request headers and payload' },
  { id: 'auth', label: 'Authentication', description: 'API authentication method' },
  { id: 'mapping', label: 'Mapping', description: 'Column mapping configuration' },
  { id: 'review', label: 'Review', description: 'Review and create' },
]

export function TaskWizard() {
  const navigate = useNavigate()
  const createTaskMutation = useCreateTask()
  const createMappingsMutation = useCreateMappings()
  const [currentStep, setCurrentStep] = useState<Step>('basic')
  const [createdTaskId, setCreatedTaskId] = useState<number | null>(null)
  const [formData, setFormData] = useState<TaskFormData>({
    name: '',
    description: '',
    endpoint_path: '',
    http_method: 'GET',
    dest_table: '',
    headers_json: {},
    body_json: {},
    batch_size: 500,
    is_active: true,
    auth_type: 'none',
  })

  const [headers, setHeaders] = useState<{ key: string; value: string }[]>([
    { key: '', value: '' },
  ])

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

  // Fetch Oracle columns when table name is set
  const { data: oracleColumnsData } = useOracleColumns(formData.dest_table || '')
  
  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep)

  const goToStep = (step: Step) => {
    setCurrentStep(step)
  }

  const goNext = () => {
    if (currentStepIndex < STEPS.length - 1) {
      const nextStep = STEPS[currentStepIndex + 1].id
      
      // Validate current step before moving
      if (currentStep === 'headers') {
        // Convert headers array to object
        const headerObj: Record<string, string> = {}
        headers.forEach(h => {
          if (h.key.trim()) {
            headerObj[h.key] = h.value
          }
        })
        setFormData(prev => ({ ...prev, headers_json: headerObj }))

        // Try to parse body JSON
        try {
          const bodyObj = bodyJson.trim() ? JSON.parse(bodyJson) : {}
          setFormData(prev => ({ ...prev, body_json: bodyObj }))
        } catch (e) {
          alert('Invalid JSON in request body')
          return
        }
      }

      if (currentStep === 'auth') {
        // Save auth data to form
        setFormData(prev => ({ 
          ...prev, 
          auth_type: authData.authType,
          api_key: authData.authType === 'bearer' ? authData.bearerToken : 
                   authData.authType === 'api_key' ? authData.apiKeyValue : '',
          username: authData.authType === 'basic' ? authData.username : '',
          password: authData.authType === 'basic' ? authData.password : '',
          oauth_config: authData.authType === 'oauth' ? 
            (() => {
              try {
                return JSON.parse(authData.oauthConfig)
              } catch {
                return null
              }
            })() : null,
        }))
      }
      
      goToStep(nextStep)
    }
  }

  const goPrev = () => {
    if (currentStepIndex > 0) {
      goToStep(STEPS[currentStepIndex - 1].id)
    }
  }

  const handleCreate = async () => {
    try {
      // Final header conversion
      const headerObj: Record<string, string> = {}
      headers.forEach(h => {
        if (h.key.trim()) {
          headerObj[h.key] = h.value
        }
      })

      let bodyObj = {}
      try {
        bodyObj = bodyJson.trim() ? JSON.parse(bodyJson) : {}
      } catch (e) {
        alert('Invalid JSON in request body')
        return
      }

      const finalData: TaskFormData = {
        ...formData,
        headers_json: headerObj,
        body_json: bodyObj,
      }

      // Basic validation
      if (!finalData.name.trim()) {
        alert('Task name is required')
        return
      }
      if (!finalData.endpoint_path.trim()) {
        alert('Endpoint URL is required')
        return
      }
      if (!finalData.dest_table.trim()) {
        alert('Table name is required')
        return
      }

      // Create the task first
      const createdTask = await createTaskMutation.mutateAsync(finalData)
      setCreatedTaskId(createdTask.id)

      // If mappings were configured, create them
      if (mappings.length > 0 && !skipMappings) {
        try {
          await createMappingsMutation.mutateAsync({
            taskId: createdTask.id,
            mappings: mappings,
          })
        } catch (mappingErr) {
          console.error('Failed to create mappings:', mappingErr)
          // Continue anyway - task was created successfully
        }
      }

      navigate('/tasks')
    } catch (err) {
      console.error('Failed to create task:', err)
    }
  }

  const handleSaveMappings = async (newMappings: ColumnMappingCreate[]) => {
    setMappings(newMappings)
    setSkipMappings(false)
    return Promise.resolve()
  }

  const handleSkipMappings = () => {
    setSkipMappings(true)
    setMappings([])
    goNext()
  }

  const canProceed = () => {
    switch (currentStep) {
      case 'basic':
        return formData.name.trim() && formData.dest_table.trim()
      case 'endpoint':
        return formData.endpoint_path.trim()
      case 'headers':
        return true
      case 'auth':
        // Validate auth fields based on type
        if (authData.authType === 'bearer') {
          return authData.bearerToken.trim() !== ''
        }
        if (authData.authType === 'api_key') {
          return authData.apiKeyHeaderName.trim() !== '' && authData.apiKeyValue.trim() !== ''
        }
        if (authData.authType === 'basic') {
          return authData.username.trim() !== '' && authData.password.trim() !== ''
        }
        return true // 'none' and 'oauth' don't require validation
      case 'mapping':
        // Allow proceed if they have at least 1 mapping OR clicked skip
        return mappings.length > 0 || skipMappings
      case 'review':
        return true
      default:
        return false
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => navigate('/tasks')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <h1 className="text-2xl font-bold">Create New Task</h1>
      </div>

      {/* Progress Steps */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            {STEPS.map((step, idx) => (
              <React.Fragment key={step.id}>
                <button
                  onClick={() => idx <= currentStepIndex && goToStep(step.id)}
                  className={`flex flex-col items-center gap-2 cursor-pointer transition ${
                    step.id === currentStep
                      ? 'opacity-100'
                      : idx <= currentStepIndex
                      ? 'opacity-100 hover:opacity-80'
                      : 'opacity-50 cursor-not-allowed'
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-medium transition ${
                      step.id === currentStep
                        ? 'bg-primary text-primary-foreground'
                        : idx < currentStepIndex
                        ? 'bg-green-600 text-white'
                        : 'bg-secondary'
                    }`}
                  >
                    {idx < currentStepIndex ? '✓' : idx + 1}
                  </div>
                  <div className="text-xs font-medium text-center">
                    <p>{step.label}</p>
                  </div>
                </button>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-2 transition ${
                      idx < currentStepIndex ? 'bg-green-600' : 'bg-secondary'
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle>{STEPS[currentStepIndex].label}</CardTitle>
          <CardDescription>{STEPS[currentStepIndex].description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Basic Info Step */}
          {currentStep === 'basic' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Task Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Sync Users, Import Products"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  placeholder="Describe what this task does"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="table">Table Name *</Label>
                <Input
                  id="table"
                  placeholder="e.g., users, products"
                  value={formData.dest_table}
                  onChange={(e) =>
                    setFormData({ ...formData, dest_table: e.target.value })
                  }
                />
              </div>
            </div>
          )}

          {/* Endpoint Step */}
          {currentStep === 'endpoint' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="endpoint">Endpoint URL *</Label>
                <Input
                  id="endpoint"
                  placeholder="https://api.example.com/users"
                  value={formData.endpoint_path}
                  onChange={(e) =>
                    setFormData({ ...formData, endpoint_path: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="method">HTTP Method *</Label>
                <select
                  id="method"
                  value={formData.http_method}
                  onChange={(e) =>
                    setFormData({ ...formData, http_method: e.target.value as 'GET' | 'POST' | 'PUT' | 'PATCH' })
                  }
                  className="w-full px-3 py-2 border rounded-md bg-background"
                >
                  <option>GET</option>
                  <option>POST</option>
                  <option>PUT</option>
                  <option>PATCH</option>
                </select>
              </div>

              <div className="p-4 bg-secondary rounded">
                <p className="text-sm text-muted-foreground">
                  <strong>Tip:</strong> Make sure the endpoint returns data in a format compatible with your target table structure.
                </p>
              </div>
            </div>
          )}

          {/* Headers & Body Step */}
          {currentStep === 'headers' && (
            <div className="space-y-6">
              <div className="space-y-3">
                <Label>Request Headers</Label>
                <div className="space-y-2">
                  {headers.map((header, idx) => (
                    <div key={idx} className="flex gap-2">
                      <Input
                        placeholder="Header name"
                        value={header.key}
                        onChange={(e) => {
                          const newHeaders = [...headers]
                          newHeaders[idx].key = e.target.value
                          setHeaders(newHeaders)
                        }}
                        className="flex-1"
                      />
                      <Input
                        placeholder="Header value"
                        value={header.value}
                        onChange={(e) => {
                          const newHeaders = [...headers]
                          newHeaders[idx].value = e.target.value
                          setHeaders(newHeaders)
                        }}
                        className="flex-1"
                      />
                      {headers.length > 1 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setHeaders(headers.filter((_, i) => i !== idx))
                          }}
                        >
                          Remove
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setHeaders([...headers, { key: '', value: '' }])}
                >
                  + Add Header
                </Button>
              </div>

              <div className="space-y-2">
                <Label htmlFor="body">Request Body (JSON)</Label>
                <textarea
                  id="body"
                  value={bodyJson}
                  onChange={(e) => setBodyJson(e.target.value)}
                  placeholder="{}"
                  className="w-full h-48 px-3 py-2 border rounded-md font-mono text-sm bg-background"
                />
                <p className="text-xs text-muted-foreground">
                  Enter valid JSON or leave empty for GET requests
                </p>
              </div>
            </div>
          )}

          {/* Authentication Step */}
          {currentStep === 'auth' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="authType">Authentication Type</Label>
                <Select value={authData.authType} onValueChange={(value) => {
                  setAuthData({
                    authType: value as AuthType,
                    bearerToken: '',
                    apiKeyHeaderName: 'X-API-Key',
                    apiKeyValue: '',
                    username: '',
                    password: '',
                    oauthConfig: '{}',
                  })
                }}>
                  <SelectTrigger id="authType">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Authentication</SelectItem>
                    <SelectItem value="bearer">Bearer Token</SelectItem>
                    <SelectItem value="api_key">API Key</SelectItem>
                    <SelectItem value="basic">Basic Auth</SelectItem>
                    <SelectItem value="oauth">OAuth 2.0</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Bearer Token */}
              {authData.authType === 'bearer' && (
                <div className="space-y-2">
                  <Label htmlFor="bearerToken">Bearer Token</Label>
                  <Input
                    id="bearerToken"
                    type="password"
                    placeholder="Enter your bearer token"
                    value={authData.bearerToken}
                    onChange={(e) => setAuthData({ ...authData, bearerToken: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">Will be sent as: Authorization: Bearer {authData.bearerToken || '[token]'}</p>
                </div>
              )}

              {/* API Key */}
              {authData.authType === 'api_key' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="apiKeyHeaderName">Header Name</Label>
                    <Input
                      id="apiKeyHeaderName"
                      placeholder="e.g., X-API-Key, api_key"
                      value={authData.apiKeyHeaderName}
                      onChange={(e) => setAuthData({ ...authData, apiKeyHeaderName: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apiKeyValue">API Key Value</Label>
                    <Input
                      id="apiKeyValue"
                      type="password"
                      placeholder="Enter your API key"
                      value={authData.apiKeyValue}
                      onChange={(e) => setAuthData({ ...authData, apiKeyValue: e.target.value })}
                    />
                    <p className="text-xs text-muted-foreground">Will be sent as: {authData.apiKeyHeaderName}: {authData.apiKeyValue || '[key]'}</p>
                  </div>
                </>
              )}

              {/* Basic Auth */}
              {authData.authType === 'basic' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      placeholder="Enter username"
                      value={authData.username}
                      onChange={(e) => setAuthData({ ...authData, username: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="Enter password"
                      value={authData.password}
                      onChange={(e) => setAuthData({ ...authData, password: e.target.value })}
                    />
                    <p className="text-xs text-muted-foreground">Will be sent as: Authorization: Basic [base64(username:password)]</p>
                  </div>
                </>
              )}

              {/* OAuth */}
              {authData.authType === 'oauth' && (
                <div className="space-y-2">
                  <Label htmlFor="oauthConfig">OAuth Configuration (JSON)</Label>
                  <textarea
                    id="oauthConfig"
                    value={authData.oauthConfig}
                    onChange={(e) => setAuthData({ ...authData, oauthConfig: e.target.value })}
                    placeholder='{"token_url": "https://...", "client_id": "...", "client_secret": "..."}'
                    className="w-full h-32 px-3 py-2 border rounded-md font-mono text-sm bg-background"
                  />
                  <p className="text-xs text-muted-foreground">Enter OAuth configuration as JSON</p>
                </div>
              )}

              {authData.authType === 'none' && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded">
                  <p className="text-sm text-blue-800">No authentication will be used for API requests</p>
                </div>
              )}
            </div>
          )}

          {/* Mapping Step */}
          {currentStep === 'mapping' && (
            <div className="space-y-4">
              {!formData.endpoint_path || !formData.dest_table ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div className="text-sm text-yellow-800">
                    <p className="font-medium">Configuration Required</p>
                    <p>Please complete the Endpoint and Basic Info steps first before configuring column mappings.</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded">
                    <p className="text-sm text-blue-800">
                      <strong>Column Mapping:</strong> Configure how API response fields map to your database columns. 
                      You can fetch a sample from your API or paste JSON manually to preview available fields.
                    </p>
                  </div>

                  {/* Render ColumnMappingEditor in wizard mode */}
                  <ColumnMappingEditor 
                    wizardMode={true}
                    taskFormData={formData}
                    existingMappings={mappings}
                    onSave={async (mappingData) => {
                      setMappings(mappingData)
                      console.log('Mappings saved:', mappingData)
                    }}
                    onFieldsLoad={() => {
                      // Fields loaded - ready to configure mappings
                      console.log('Fields loaded successfully')
                    }}
                  />
                </>
              )}
            </div>
          )}

          {/* Review Step */}
          {currentStep === 'review' && (
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="p-3 bg-secondary rounded">
                  <p className="text-sm"><strong>Name:</strong> {formData.name}</p>
                </div>
                <div className="p-3 bg-secondary rounded">
                  <p className="text-sm"><strong>Description:</strong> {formData.description || '(None)'}</p>
                </div>
                <div className="p-3 bg-secondary rounded">
                  <p className="text-sm"><strong>Endpoint:</strong> {formData.http_method} {formData.endpoint_path}</p>
                </div>
                <div className="p-3 bg-secondary rounded">
                  <p className="text-sm"><strong>Table:</strong> {formData.dest_table}</p>
                </div>
                {Object.keys(formData.headers_json || {}).length > 0 && (
                  <div className="p-3 bg-secondary rounded">
                    <p className="text-sm font-medium mb-2"><strong>Headers:</strong></p>
                    <div className="text-xs space-y-1">
                      {Object.entries(formData.headers_json).map(([k, v]) => (
                        <p key={k}><span className="font-mono">{k}:</span> {String(v)}</p>
                      ))}
                    </div>
                  </div>
                )}
                {formData.auth_type && formData.auth_type !== 'none' && (
                  <div className="p-3 bg-secondary rounded">
                    <p className="text-sm font-medium mb-2"><strong>Authentication:</strong></p>
                    <p className="text-xs">
                      Type: <span className="font-mono capitalize">{formData.auth_type}</span>
                    </p>
                    {formData.auth_type === 'basic' && formData.username && (
                      <p className="text-xs mt-1">Username: <span className="font-mono">{formData.username}</span></p>
                    )}
                  </div>
                )}
                {mappings.length > 0 && (
                  <div className="p-3 bg-secondary rounded">
                    <p className="text-sm font-medium mb-2"><strong>Column Mappings:</strong> {mappings.length} configured</p>
                    <div className="text-xs space-y-1 max-h-32 overflow-y-auto">
                      {mappings.map((m, idx) => (
                        <p key={idx} className="font-mono">
                          {m.source_field} → {m.dest_column}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
                {skipMappings && mappings.length === 0 && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded">
                    <p className="text-sm text-amber-800">
                      ⚠️ <strong>No column mappings configured.</strong> You'll need to configure mappings in the Task Detail page before running this task.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex justify-between gap-2">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={currentStepIndex === 0}
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          Previous
        </Button>

        {currentStep === 'review' ? (
          <Button
            onClick={handleCreate}
            disabled={createTaskMutation.isPending || !canProceed()}
            className="gap-2"
          >
            {createTaskMutation.isPending ? 'Creating...' : 'Create Task'}
          </Button>
        ) : (
          <Button
            onClick={goNext}
            disabled={!canProceed()}
            className="gap-2"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
