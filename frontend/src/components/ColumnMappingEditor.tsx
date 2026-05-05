import React, { useState, useEffect, useMemo } from 'react'
import {
  ColumnMapping, ColumnMappingCreate, FieldPreview, OracleColumn,
  TaskFormData,
} from '@/types'
import { Card, Button, Input, Select, Tag, Space, Typography, Alert, Tree } from 'antd'
import {
  DeleteOutlined, PlusOutlined, CopyOutlined,
} from '@ant-design/icons'
import { apiClient } from '@/api/client'
import { useOracleColumns } from '@/hooks/api'
import type { DataNode } from 'antd/es/tree'
import type { AxiosError } from 'axios'

const { Text } = Typography

interface ColumnMappingEditorProps {
  taskId?: number
  fields?: FieldPreview[]
  oracleColumns?: OracleColumn[]
  existingMappings?: Array<ColumnMapping | ColumnMappingCreate>
  onSave?: (mappings: ColumnMappingCreate[]) => Promise<void>
  onFieldsLoad?: () => void
  isLoading?: boolean
  readOnly?: boolean
  wizardMode?: boolean
  taskFormData?: TaskFormData
}

interface MappingRow {
  id: string
  sourceField: string
  destColumn: string
  transforms: string[]
}

const AVAILABLE_TRANSFORMS = ['trim', 'upper', 'lower', 'to_int', 'to_float', 'to_date', 'to_timestamp']

const shellQuote = (value: string) => `'${value.replace(/'/g, "'\\''")}'`

const stringifyValue = (value: unknown) => {
  if (value === undefined || value === null) return ''
  return typeof value === 'string' ? value : JSON.stringify(value)
}

const buildCurlCommand = (taskFormData?: TaskFormData) => {
  if (!taskFormData?.endpoint_path) return ''

  const method = taskFormData.http_method || 'GET'
  let url: URL
  try {
    url = new URL(taskFormData.endpoint_path)
  } catch {
    return `curl -X ${method} ${shellQuote(taskFormData.endpoint_path)}`
  }
  Object.entries(taskFormData.query_params_json || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, stringifyValue(value))
    }
  })

  const headers: Record<string, string> = {}
  Object.entries(taskFormData.headers_json || {}).forEach(([key, value]) => {
    if (key.trim()) headers[key] = stringifyValue(value)
  })

  if (taskFormData.auth_type === 'bearer' && taskFormData.api_key) {
    headers.Authorization = `Bearer ${taskFormData.api_key}`
  }
  if (taskFormData.auth_type === 'api_key' && taskFormData.api_key) {
    const headerName = taskFormData.oauth_config?.api_key_header || 'X-API-Key'
    headers[headerName] = taskFormData.api_key
  }
  if (taskFormData.auth_type === 'basic' && taskFormData.username && taskFormData.password) {
    headers.Authorization = `Basic ${btoa(`${taskFormData.username}:${taskFormData.password}`)}`
  }
  if (taskFormData.auth_type === 'oauth') {
    const token = taskFormData.oauth?.access_token || taskFormData.oauth_config?.access_token
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const parts = ['curl', '-X', method, shellQuote(url.toString())]
  Object.entries(headers).forEach(([key, value]) => {
    parts.push('-H', shellQuote(`${key}: ${value}`))
  })
  if (taskFormData.body_json && Object.keys(taskFormData.body_json).length > 0) {
    parts.push('-H', shellQuote('Content-Type: application/json'))
    parts.push('--data', shellQuote(JSON.stringify(taskFormData.body_json)))
  }
  return parts.join(' ')
}

const getPreviewErrorMessage = (err: unknown) => {
  const axiosError = err as AxiosError<{ detail?: unknown }>
  const detail = axiosError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  if (err instanceof Error) return err.message
  return 'Unknown error'
}

export const ColumnMappingEditor: React.FC<ColumnMappingEditorProps> = ({
  fields = [], oracleColumns = [], existingMappings = [],
  onSave, onFieldsLoad, isLoading = false, readOnly = false,
  wizardMode = false, taskFormData,
}) => {
  const [mappings, setMappings] = useState<MappingRow[]>([])
  const [selectedSampleTab, setSelectedSampleTab] = useState<'auto' | 'manual'>('auto')
  const [manualSampleJson, setManualSampleJson] = useState('')
  const [sampleError, setSampleError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isFetching, setIsFetching] = useState(false)
  const [fetchedFields, setFetchedFields] = useState<FieldPreview[]>([])
  const curlCommand = useMemo(() => buildCurlCommand(taskFormData), [taskFormData])

  const tableName = taskFormData?.dest_table || ''
  const connectionId = taskFormData?.connection_id
  const hasSelectedConnection = !!connectionId
  const { data: fetchedOracleColumnsData, isLoading: isLoadingColumns, error: columnsError } = useOracleColumns(tableName, connectionId)
  const fetchedOracleColumns = fetchedOracleColumnsData?.columns || []
  const activeOracleColumns = fetchedOracleColumns.length > 0 ? fetchedOracleColumns : oracleColumns
  const hasLoadedColumns = activeOracleColumns.length > 0
  const shouldShowColumnLoadError = !!columnsError && !hasLoadedColumns

  // Build tree data from fields
  const treeData = useMemo((): DataNode[] => {
    const sourceFields = fetchedFields.length > 0 ? fetchedFields : fields
    const rootNodes: Record<string, DataNode> = {}

    sourceFields.forEach((field) => {
      const parts = field.field_name.split('.')
      if (parts.length === 1) {
        rootNodes[field.field_name] = {
          title: (
            <Space size="small">
              <Text code style={{ fontSize: 12 }}>{field.field_name}</Text>
              <Tag style={{ fontSize: 10 }}>{field.field_type}</Tag>
              <Button
                type="text" size="small"
                icon={<CopyOutlined />}
                onClick={() => navigator.clipboard.writeText(field.field_name)}
              />
            </Space>
          ),
          key: field.field_name,
          isLeaf: true,
        }
      }
    })

    // For nested fields, just show them flat as leaves for simplicity
    sourceFields.forEach((field) => {
      if (field.field_name.includes('.') && !rootNodes[field.field_name]) {
        rootNodes[field.field_name] = {
          title: (
            <Space size="small">
              <Text code style={{ fontSize: 12 }}>{field.field_name}</Text>
              <Tag style={{ fontSize: 10 }}>{field.field_type}</Tag>
              <Button
                type="text" size="small"
                icon={<CopyOutlined />}
                onClick={() => navigator.clipboard.writeText(field.field_name)}
              />
            </Space>
          ),
          key: field.field_name,
          isLeaf: true,
        }
      }
    })

    return Object.values(rootNodes)
  }, [fields, fetchedFields])

  useEffect(() => {
    if (existingMappings && existingMappings.length > 0) {
      const rows = existingMappings.map((m, idx) => {
        let transforms: string[] = []
        const transformRules = m.transform_rules
        if (Array.isArray(transformRules)) transforms = transformRules
        else if (typeof transformRules === 'string') {
          try { transforms = JSON.parse(transformRules) } catch { transforms = [] }
        } else if (transformRules && typeof transformRules === 'object') {
          const mt = (transformRules as { transforms?: string[] }).transforms
          transforms = Array.isArray(mt) ? mt : []
        }
        const id = 'id' in m && m.id !== undefined ? m.id.toString() : `temp-${Date.now()}-${idx}`
        return { id, sourceField: m.source_field, destColumn: m.dest_column, transforms }
      })
      setMappings(rows)
    }
  }, [existingMappings])

  const handleAutoFetch = async () => {
    if (!wizardMode || !taskFormData) return
    setIsFetching(true); setSampleError(null)
    try {
      const preview = await apiClient.previewMappingFieldsStandalone({
        use_auto_fetch: true, method: taskFormData.http_method, url: taskFormData.endpoint_path,
        headers: taskFormData.headers_json as Record<string, string>,
        params: taskFormData.query_params_json, json_body: taskFormData.body_json,
        record_path: taskFormData.record_path,
        auth_type: taskFormData.auth_type,
        api_key: taskFormData.api_key,
        username: taskFormData.username,
        password: taskFormData.password,
        oauth_config: taskFormData.oauth || taskFormData.oauth_config,
      })
      setFetchedFields(preview.fields); onFieldsLoad?.()
    } catch (err) {
      setSampleError(`Failed to fetch sample response: ${getPreviewErrorMessage(err)}`)
    } finally { setIsFetching(false) }
  }

  const handleParseSampleJson = async () => {
    if (!manualSampleJson.trim()) { setSampleError('Please paste JSON content'); return }
    setIsFetching(true); setSampleError(null)
    try {
      const jsonData = JSON.parse(manualSampleJson)
      const preview = await apiClient.previewMappingFieldsStandalone({
        use_auto_fetch: false, sample_json: jsonData,
        record_path: wizardMode && taskFormData ? taskFormData.record_path : undefined,
      })
      setFetchedFields(preview.fields); onFieldsLoad?.()
    } catch (err) {
      setSampleError(`Invalid JSON: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally { setIsFetching(false) }
  }

  const addMappingRow = () => {
    setMappings(prev => [...prev, { id: Date.now().toString(), sourceField: '', destColumn: '', transforms: [] }])
  }

  const updateMapping = (id: string, updates: Partial<MappingRow>) => {
    setMappings(prev => prev.map(m => m.id === id ? { ...m, ...updates } : m))
  }

  const removeMapping = (id: string) => { setMappings(prev => prev.filter(m => m.id !== id)) }

  const toggleTransform = (id: string, transform: string) => {
    const mapping = mappings.find(m => m.id === id)
    if (!mapping) return
    const newTransforms = mapping.transforms.includes(transform)
      ? mapping.transforms.filter(t => t !== transform)
      : [...mapping.transforms, transform]
    updateMapping(id, { transforms: newTransforms })
  }

  const handleSave = async () => {
    if (mappings.length === 0) { setSampleError('At least one mapping is required'); return }

    // Filter out incomplete mappings (empty source or dest)
    const validMappings = mappings.filter(m => m.sourceField.trim() && m.destColumn.trim())

    if (validMappings.length === 0) {
      setSampleError('At least one complete mapping (source field + destination column) is required')
      return
    }

    setIsSaving(true); setSampleError(null); setSuccessMessage(null)
    try {
      const data: ColumnMappingCreate[] = validMappings.map(m => ({
        source_field: m.sourceField, dest_column: m.destColumn,
        transform_rules: m.transforms.length > 0 ? m.transforms : undefined,
        is_active: true,
      }))
      if (onSave) await onSave(data)
      setSuccessMessage(`Saved ${validMappings.length} mapping${validMappings.length !== 1 ? 's' : ''}`)
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      setSampleError(err instanceof Error ? err.message : 'Failed to save')
    } finally { setIsSaving(false) }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Step 1: Load Sample Data */}
      <Card size="small" title="Step 1: Load Sample Data">
        <Space style={{ marginBottom: 12 }}>
          <Button
            type={selectedSampleTab === 'auto' ? 'primary' : 'default'} size="small"
            onClick={() => setSelectedSampleTab('auto')}
          >Auto-Fetch</Button>
          <Button
            type={selectedSampleTab === 'manual' ? 'primary' : 'default'} size="small"
            onClick={() => setSelectedSampleTab('manual')}
          >Manual Paste</Button>
        </Space>

        {selectedSampleTab === 'auto' && (
          <>
            <Button block onClick={handleAutoFetch} loading={isFetching || isLoading}>
              Fetch Sample from API
            </Button>
            {curlCommand && (
              <Card size="small" title="Generated cURL" style={{ marginTop: 8 }}>
                <Typography.Paragraph
                  code
                  copyable={{ text: curlCommand }}
                  style={{ marginBottom: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                >
                  {curlCommand}
                </Typography.Paragraph>
              </Card>
            )}
          </>
        )}

        {selectedSampleTab === 'manual' && (
          <>
            <Input.TextArea
              value={manualSampleJson}
              onChange={(e) => { setManualSampleJson(e.target.value); setSampleError(null) }}
              placeholder='Paste JSON response here'
              rows={4}
              style={{ fontFamily: 'monospace', marginBottom: 8 }}
            />
            <Button block onClick={handleParseSampleJson} disabled={!manualSampleJson.trim()} loading={isFetching}>
              Parse JSON
            </Button>
          </>
        )}

        {sampleError && <Alert message={sampleError} type="error" showIcon style={{ marginTop: 8 }} />}
        {successMessage && <Alert message={successMessage} type="success" showIcon style={{ marginTop: 8 }} />}

        {taskFormData && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
            Connection: <strong>{connectionId || '(not selected)'}</strong> | Table: <strong>{tableName || '(not set)'}</strong> | Columns: {isLoadingColumns ? 'Loading...' : `${activeOracleColumns.length} found`}
            {shouldShowColumnLoadError && <span style={{ color: '#ff4d4f' }}> | Column auto-load not available</span>}
          </div>
        )}
        {taskFormData && !hasSelectedConnection && (
          <Alert
            message="Destination connection required"
            description="Select a destination connection first so column metadata can be loaded for mappings."
            type="warning"
            showIcon
            style={{ marginTop: 8 }}
          />
        )}
      </Card>

      {/* Field Preview + Mappings */}
      {fetchedFields.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Card size="small" title={`Available API Fields (${fetchedFields.length})`}>
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              <Tree treeData={treeData} defaultExpandAll showLine />
            </div>
          </Card>

          <Card size="small" title="Column Mappings">
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              {mappings.map((mapping) => (
                <Card key={mapping.id} size="small" style={{ marginBottom: 8, background: '#fafafa' }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Space style={{ width: '100%' }}>
                      <Input
                        placeholder="API field (e.g., user.name)"
                        value={mapping.sourceField}
                        onChange={(e) => updateMapping(mapping.id, { sourceField: e.target.value })}
                        disabled={readOnly}
                        style={{ flex: 1 }}
                      />
                      <Button danger icon={<DeleteOutlined />} size="small" onClick={() => removeMapping(mapping.id)} disabled={readOnly} />
                    </Space>

                    {hasLoadedColumns ? (
                      <Select
                        value={mapping.destColumn || undefined}
                        onChange={(v) => updateMapping(mapping.id, { destColumn: v })}
                        placeholder="Select DB Column"
                        disabled={readOnly}
                        options={activeOracleColumns.map(col => ({
                          value: col.column_name,
                          label: `${col.column_name} (${col.data_type})`,
                        }))}
                        style={{ width: '100%' }}
                      />
                    ) : (
                      <Input
                        placeholder="Destination column (e.g., PRODUCT_ID)"
                        value={mapping.destColumn}
                        onChange={(e) => updateMapping(mapping.id, { destColumn: e.target.value })}
                        disabled={readOnly}
                      />
                    )}

                    <Space wrap>
                      {AVAILABLE_TRANSFORMS.map((t) => (
                        <Tag
                          key={t}
                          color={mapping.transforms.includes(t) ? 'blue' : undefined}
                          onClick={() => !readOnly && toggleTransform(mapping.id, t)}
                          style={{ cursor: readOnly ? 'default' : 'pointer' }}
                        >
                          {t}
                        </Tag>
                      ))}
                    </Space>
                  </Space>
                </Card>
              ))}

              {mappings.length === 0 && (
                <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
                  No mappings yet. Add one to get started.
                </Text>
              )}
            </div>

            <Button icon={<PlusOutlined />} block onClick={addMappingRow} disabled={readOnly} style={{ marginTop: 8 }}>
              Add Mapping
            </Button>
          </Card>
        </div>
      )}

      {/* Actions */}
      {!readOnly && mappings.length > 0 && (
        <>
          {mappings.some(m => !m.sourceField || !m.destColumn) && (
            <Alert message="All mappings must have both Source Field and Destination Column filled in" type="warning" showIcon />
          )}
          <Space style={{ justifyContent: 'flex-end', width: '100%', display: 'flex' }}>
            <Button onClick={() => setMappings([])}>Clear All</Button>
            <Button type="primary" onClick={handleSave} loading={isSaving}
              disabled={mappings.some(m => !m.sourceField || !m.destColumn)}>
              Save Mappings
            </Button>
          </Space>
        </>
      )}

      {mappings.length === 0 && fetchedFields.length > 0 && (
        <Alert message="At least one mapping is required to proceed" type="warning" showIcon />
      )}
    </Space>
  )
}
