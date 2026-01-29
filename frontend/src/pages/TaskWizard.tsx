import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateTask } from '@/hooks/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, ChevronRight, ChevronLeft } from 'lucide-react'
import { TaskFormData } from '@/types'

type Step = 'basic' | 'endpoint' | 'headers' | 'mapping' | 'review'

const STEPS: { id: Step; label: string; description: string }[] = [
  { id: 'basic', label: 'Basic Info', description: 'Task name and description' },
  { id: 'endpoint', label: 'Endpoint', description: 'API endpoint configuration' },
  { id: 'headers', label: 'Headers & Body', description: 'Request headers and payload' },
  { id: 'mapping', label: 'Mapping', description: 'Column mapping configuration' },
  { id: 'review', label: 'Review', description: 'Review and create' },
]

export function TaskWizard() {
  const navigate = useNavigate()
  const createTaskMutation = useCreateTask()
  const [currentStep, setCurrentStep] = useState<Step>('basic')
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
  })

  const [headers, setHeaders] = useState<{ key: string; value: string }[]>([
    { key: '', value: '' },
  ])

  const [bodyJson, setBodyJson] = useState('{}')

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

      await createTaskMutation.mutateAsync(finalData)
      navigate('/tasks')
    } catch (err) {
      console.error('Failed to create task:', err)
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 'basic':
        return formData.name.trim() && formData.dest_table.trim()
      case 'endpoint':
        return formData.endpoint_path.trim()
      case 'headers':
        return true
      case 'mapping':
        return true
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

          {/* Mapping Step */}
          {currentStep === 'mapping' && (
            <div className="space-y-4">
              <div className="p-4 bg-secondary rounded">
                <p className="text-sm text-muted-foreground">
                  <strong>Column Mapping:</strong> The system will automatically map API response fields to your database table columns. 
                  You can configure advanced mappings after task creation.
                </p>
              </div>
              <div className="p-4 border-2 border-dashed rounded text-center">
                <p className="text-muted-foreground">
                  <strong>Endpoint:</strong> {formData.endpoint_path || 'Not set'}
                </p>
                <p className="text-muted-foreground">
                  <strong>Table:</strong> {formData.dest_table || 'Not set'}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Column mapping will be configured based on the first API response received
                </p>
              </div>
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
