import React, { useState, useEffect, useMemo } from 'react'
import {
  ColumnMapping,
  ColumnMappingCreate,
  FieldPreview,
  OracleColumn,
  TransformSuggestion,
  TaskFormData,
} from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { ChevronDown, ChevronRight, Copy, Trash2, Plus, AlertCircle, Loader } from 'lucide-react'
import { apiClient } from '@/api/client'
import { useOracleColumns } from '@/hooks/api'

interface ColumnMappingEditorProps {
  taskId?: number
  fields?: FieldPreview[]
  oracleColumns?: OracleColumn[]
  existingMappings?: Array<ColumnMapping | ColumnMappingCreate>
  onSave?: (mappings: ColumnMappingCreate[]) => Promise<void>
  onFieldsLoad?: () => void
  isLoading?: boolean
  readOnly?: boolean
  // For wizard mode (standalone, without task ID)
  wizardMode?: boolean
  taskFormData?: TaskFormData
}

interface ExpandedTreeNode {
  [key: string]: boolean
}

interface MappingRow {
  id: string
  sourceField: string
  destColumn: string
  transforms: string[]
  suggestions?: TransformSuggestion[]
}

export const ColumnMappingEditor: React.FC<ColumnMappingEditorProps> = ({
  taskId,
  fields = [],
  oracleColumns = [],
  existingMappings = [],
  onSave,
  onFieldsLoad,
  isLoading = false,
  readOnly = false,
  wizardMode = false,
  taskFormData,
}) => {
  const [expandedNodes, setExpandedNodes] = useState<ExpandedTreeNode>({})
  const [mappings, setMappings] = useState<MappingRow[]>([])
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [selectedSampleTab, setSelectedSampleTab] = useState<'auto' | 'manual'>('auto')
  const [manualSampleJson, setManualSampleJson] = useState('')
  const [sampleError, setSampleError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isFetching, setIsFetching] = useState(false)
  const [fetchedFields, setFetchedFields] = useState<FieldPreview[]>([])

  // Fetch Oracle columns based on table name
  const tableName = wizardMode ? taskFormData?.dest_table || '' : ''
  const { data: fetchedOracleColumnsData, isLoading: isLoadingColumns, error: columnsError } = useOracleColumns(tableName)
  const fetchedOracleColumns = fetchedOracleColumnsData?.columns || []
  const activeOracleColumns = fetchedOracleColumns.length > 0 ? fetchedOracleColumns : oracleColumns

  // Debug logging
  useEffect(() => {
    console.log('ColumnMappingEditor - Debug Info:', {
      wizardMode,
      tableName,
      taskFormData: taskFormData?.dest_table,
      fetchedOracleColumnsCount: fetchedOracleColumns.length,
      isLoadingColumns,
      columnsError,
    })
  }, [wizardMode, tableName, fetchedOracleColumns, isLoadingColumns, columnsError])

  // Build hierarchical tree structure from flattened fields
  const fieldTree = useMemo(() => {
    const tree: Record<string, any> = {}
    const sourcFields = fetchedFields.length > 0 ? fetchedFields : fields

    sourcFields.forEach((field: FieldPreview) => {
      if (!field.parent_path) {
        // Root level field
        tree[field.field_name] = field
      } else {
        // Nested field - create parent path
        const parts = field.field_name.split('.')
        let current = tree

        parts.forEach((part, idx) => {
          if (idx === parts.length - 1) {
            // Last part - the actual field
            current[part] = field
          } else {
            // Intermediate part - create container
            if (!current[part]) {
              current[part] = {}
            }
            current = current[part]
          }
        })
      }
    })

    return tree
  }, [fields, fetchedFields])

  // Load existing mappings on mount
  useEffect(() => {
    if (existingMappings && existingMappings.length > 0) {
      const rows = existingMappings.map((m, idx) => {
        const transformRules = m.transform_rules
        let transforms: string[] = []

        if (Array.isArray(transformRules)) {
          transforms = transformRules
        } else if (typeof transformRules === 'string') {
          try {
            transforms = JSON.parse(transformRules) as string[]
          } catch {
            transforms = []
          }
        } else if (transformRules && typeof transformRules === 'object') {
          const maybeTransforms = (transformRules as { transforms?: string[] }).transforms
          transforms = Array.isArray(maybeTransforms) ? maybeTransforms : []
        }

        const id = 'id' in m && m.id !== undefined ? m.id.toString() : `temp-${Date.now()}-${idx}`

        return {
          id,
          sourceField: m.source_field,
          destColumn: m.dest_column,
          transforms,
          suggestions: undefined,
        }
      })
      setMappings(rows)
    }
  }, [existingMappings])

  // Copy field path to clipboard
  const copyFieldPath = (fieldName: string) => {
    navigator.clipboard.writeText(fieldName)
    setCopiedField(fieldName)
    setTimeout(() => setCopiedField(null), 2000)
  }

  // Toggle tree node expansion
  const toggleNodeExpanded = (nodePath: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodePath]: !prev[nodePath],
    }))
  }

  // Handle auto-fetch from API
  const handleAutoFetch = async () => {
    if (!wizardMode || !taskFormData) {
      console.error('Auto-fetch only supported in wizard mode')
      return
    }

    setIsFetching(true)
    setSampleError(null)

    try {
      console.log('Fetching from API:', {
        method: taskFormData.http_method,
        url: taskFormData.endpoint_path,
      })

      const preview = await apiClient.previewMappingFieldsStandalone({
        use_auto_fetch: true,
        method: taskFormData.http_method,
        url: taskFormData.endpoint_path,
        headers: taskFormData.headers_json,
        params: taskFormData.query_params_json,
        json_body: taskFormData.body_json,
        record_path: taskFormData.record_path,
      })

      console.log('Preview received:', preview)
      setFetchedFields(preview.fields)
      setSampleError(null)
      onFieldsLoad?.()
    } catch (err) {
      console.error('Auto-fetch error:', err)
      setSampleError(
        `Failed to fetch from API: ${err instanceof Error ? err.message : 'Unknown error'}`
      )
    } finally {
      setIsFetching(false)
    }
  }

  // Handle sample JSON parsing
  const handleParseSampleJson = async () => {
    if (!manualSampleJson.trim()) {
      setSampleError('Please paste JSON content')
      return
    }

    setIsFetching(true)
    setSampleError(null)

    try {
      console.log('Parsing manual JSON...')
      const jsonData = JSON.parse(manualSampleJson)
      console.log('Parsed JSON:', jsonData)

      const preview = await apiClient.previewMappingFieldsStandalone({
        use_auto_fetch: false,
        sample_json: jsonData,
        record_path: wizardMode && taskFormData ? taskFormData.record_path : undefined,
      })

      console.log('Preview received:', preview)
      setFetchedFields(preview.fields)
      setSampleError(null)
      onFieldsLoad?.()
    } catch (err) {
      console.error('Parse error:', err)
      setSampleError(`Invalid JSON: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsFetching(false)
    }
  }

  // Add new mapping row
  const addMappingRow = () => {
    const newRow: MappingRow = {
      id: Date.now().toString(),
      sourceField: '',
      destColumn: '',
      transforms: [],
    }
    setMappings((prev) => [...prev, newRow])
  }

  // Update mapping row
  const updateMapping = (id: string, updates: Partial<MappingRow>) => {
    setMappings((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    )
  }

  // Remove mapping row
  const removeMapping = (id: string) => {
    setMappings((prev) => prev.filter((m) => m.id !== id))
  }

  // Toggle transform for mapping
  const toggleTransform = (id: string, transform: string) => {
    updateMapping(id, {
      transforms: mappings
        .find((m) => m.id === id)
        ?.transforms.includes(transform)
        ? mappings.find((m) => m.id === id)!.transforms.filter((t) => t !== transform)
        : [...(mappings.find((m) => m.id === id)?.transforms || []), transform],
    })
  }

  // Get suggested transforms for a mapping (stub - would call backend in real app)
  const _getSuggestedTransforms = (sourceType?: string): TransformSuggestion[] => {
    if (!sourceType || sourceType === 'null') {
      return []
    }

    const suggestions: Record<string, TransformSuggestion[]> = {
      string: [
        { transform_name: 'trim', description: 'Remove whitespace', confidence: 'high', reason: 'String cleanup' },
        { transform_name: 'upper', description: 'Uppercase', confidence: 'medium', reason: 'Case conversion' },
        { transform_name: 'lower', description: 'Lowercase', confidence: 'medium', reason: 'Case conversion' },
      ],
      number: [
        { transform_name: 'to_int', description: 'Convert to integer', confidence: 'high', reason: 'Type conversion' },
        { transform_name: 'to_float', description: 'Convert to float', confidence: 'high', reason: 'Type conversion' },
      ],
    }

    return suggestions[sourceType] || []
  }

  // Save all mappings
  const handleSave = async () => {
    if (mappings.length === 0) {
      setSampleError('At least one mapping is required')
      setSuccessMessage(null)
      return
    }

    setIsSaving(true)
    setSampleError(null)
    setSuccessMessage(null)
    
    try {
      const mappingData: ColumnMappingCreate[] = mappings.map((m) => ({
        source_field: m.sourceField,
        dest_column: m.destColumn,
        transform_rules: m.transforms.length > 0 ? JSON.stringify(m.transforms) : undefined,
        is_active: true,
      }))

      if (onSave) {
        await onSave(mappingData)
      }
      
      // Show success message
      const successMsg = `✓ Saved ${mappings.length} mapping${mappings.length !== 1 ? 's' : ''}`
      setSuccessMessage(successMsg)
      
      // Clear after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to save mappings'
      setSampleError(errorMsg)
      setSuccessMessage(null)
    } finally {
      setIsSaving(false)
    }
  }

  // Render tree node recursively
  const renderTreeNode = (
    nodePath: string,
    nodeData: any,
    depth: number = 0
  ): React.ReactNode => {
    if (!nodeData || typeof nodeData !== 'object') {
      return null
    }

    const isExpanded = expandedNodes[nodePath]
    const entries = Object.entries(nodeData)
    const hasChildren = entries.length > 0

    return (
      <div key={nodePath} className="space-y-1">
        {entries.map(([key, value]) => {
          const currentPath = nodePath ? `${nodePath}.${key}` : key
          const isLeaf = (value as FieldPreview)?.field_type !== undefined
          const fieldInfo = value as FieldPreview | undefined

          return (
            <div key={currentPath} className="space-y-1">
              <div
                className="flex items-center gap-2 px-3 py-2 hover:bg-slate-100 rounded cursor-pointer text-sm"
                style={{ paddingLeft: `${12 + depth * 16}px` }}
              >
                {!isLeaf && hasChildren && (
                  <button
                    onClick={() => toggleNodeExpanded(currentPath)}
                    className="p-0 hover:bg-slate-200 rounded"
                  >
                    {isExpanded ? (
                      <ChevronDown size={16} />
                    ) : (
                      <ChevronRight size={16} />
                    )}
                  </button>
                )}
                {isLeaf && (
                  <span className="w-4" />
                )}

                <span className="flex-1 font-mono text-xs">{key}</span>

                {isLeaf && fieldInfo && (
                  <>
                    <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded">
                      {fieldInfo.field_type}
                    </span>
                    <button
                      onClick={() => copyFieldPath(currentPath)}
                      className="p-1 hover:bg-slate-200 rounded"
                      title="Copy field path"
                    >
                      <Copy size={14} />
                    </button>
                    {copiedField === currentPath && (
                      <span className="text-xs text-green-600">Copied!</span>
                    )}
                  </>
                )}
              </div>

              {!isLeaf && isExpanded && renderTreeNode(currentPath, value, depth + 1)}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Sample Data Section */}
      <Card className="p-4">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <span>Step 1: Load Sample Data</span>
          {fields.length === 0 && <AlertCircle size={16} className="text-yellow-600" />}
        </h3>

        <div className="space-y-3">
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setSelectedSampleTab('auto')}
              className={`px-3 py-1 rounded text-sm ${
                selectedSampleTab === 'auto'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-200'
              }`}
            >
              Auto-Fetch
            </button>
            <button
              onClick={() => setSelectedSampleTab('manual')}
              className={`px-3 py-1 rounded text-sm ${
                selectedSampleTab === 'manual'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-200'
              }`}
            >
              Manual Paste
            </button>
          </div>

          {selectedSampleTab === 'auto' && (
            <Button
              onClick={handleAutoFetch}
              disabled={isFetching || isLoading}
              className="w-full"
            >
              {isFetching || isLoading ? (
                <>
                  <Loader size={16} className="mr-2 animate-spin" />
                  Fetching...
                </>
              ) : (
                'Fetch Sample from API'
              )}
            </Button>
          )}

          {selectedSampleTab === 'manual' && (
            <>
              <textarea
                value={manualSampleJson}
                onChange={(e) => {
                  setManualSampleJson(e.target.value)
                  setSampleError(null)
                }}
                placeholder='Paste JSON response here (e.g., {"user": {"name": "Alice"}})'
                className="w-full h-32 p-3 border rounded font-mono text-sm"
              />
              <Button
                onClick={handleParseSampleJson}
                disabled={!manualSampleJson.trim() || isFetching}
                className="w-full"
              >
                {isFetching ? (
                  <>
                    <Loader size={16} className="mr-2 animate-spin" />
                    Parsing...
                  </>
                ) : (
                  'Parse JSON'
                )}
              </Button>
            </>
          )}

          {sampleError && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded flex items-center gap-2">
              <AlertCircle size={16} />
              {sampleError}
            </div>
          )}

          {successMessage && (
            <div className="text-sm text-green-700 bg-green-50 p-3 rounded flex items-center gap-2">
              <AlertCircle size={16} />
              {successMessage}
            </div>
          )}

          {/* Debug Info - Oracle Columns Status */}
          {wizardMode && (
            <div className="text-xs text-slate-600 bg-slate-50 p-2 rounded mt-2">
              <div>Table: <strong>{tableName || '(not set)'}</strong></div>
              <div>Columns: {isLoadingColumns ? 'Loading...' : `${activeOracleColumns.length} found`}</div>
              {columnsError && <div className="text-red-600 text-xs">Note: Column auto-load not available. Enter column names manually.</div>}
            </div>
          )}
        </div>
      </Card>

      {/* Field Preview Section */}
      {fetchedFields.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* API Fields Tree */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Available API Fields ({fetchedFields.length})</h3>
            <div className="border rounded bg-white max-h-96 overflow-y-auto">
              {renderTreeNode('', fieldTree)}
            </div>
          </Card>

          {/* Mappings Configuration */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Column Mappings</h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {mappings.map((mapping) => (
                <div
                  key={mapping.id}
                  className="p-3 border rounded bg-slate-50 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Input
                      placeholder="API field (e.g., user.name)"
                      value={mapping.sourceField}
                      onChange={(e) =>
                        updateMapping(mapping.id, { sourceField: e.target.value })
                      }
                      disabled={readOnly}
                      className="text-sm"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeMapping(mapping.id)}
                      disabled={readOnly}
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>

                  {/* DB Column Selection - either dropdown or text input */}
                  {activeOracleColumns.length > 0 ? (
                    <select
                      value={mapping.destColumn}
                      onChange={(e) =>
                        updateMapping(mapping.id, { destColumn: e.target.value })
                      }
                      disabled={readOnly}
                      className="w-full px-2 py-1 border rounded text-sm"
                    >
                      <option value="">Select DB Column</option>
                      {activeOracleColumns.map((col: OracleColumn) => (
                        <option key={col.column_name} value={col.column_name}>
                          {col.column_name} ({col.data_type})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <Input
                      placeholder="Enter destination column name (e.g., PRODUCT_ID)"
                      value={mapping.destColumn}
                      onChange={(e) =>
                        updateMapping(mapping.id, { destColumn: e.target.value })
                      }
                      disabled={readOnly}
                      className="text-sm"
                    />
                  )}

                  {/* Transforms */}
                  <div className="flex gap-1 flex-wrap">
                    {['trim', 'upper', 'lower', 'to_int', 'to_float', 'to_timestamp'].map(
                      (transform) => (
                        <button
                          key={transform}
                          onClick={() => !readOnly && toggleTransform(mapping.id, transform)}
                          className={`px-2 py-1 rounded text-xs font-medium transition ${
                            mapping.transforms.includes(transform)
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                          } ${readOnly ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          {transform}
                        </button>
                      )
                    )}
                  </div>
                </div>
              ))}

              {mappings.length === 0 && (
                <div className="text-center py-8 text-slate-500">
                  No mappings yet. Add one to get started.
                </div>
              )}
            </div>

            <Button
              onClick={addMappingRow}
              disabled={readOnly}
              className="w-full mt-3"
              variant="outline"
            >
              <Plus size={16} className="mr-2" />
              Add Mapping
            </Button>
          </Card>
        </div>
      )}

      {/* Action Buttons */}
      {!readOnly && mappings.length > 0 && (
        <div className="flex flex-col gap-3 pt-4">
          {/* Validation warning if button would be disabled */}
          {mappings.some((m) => !m.sourceField || !m.destColumn) && (
            <div className="text-xs text-amber-700 bg-amber-50 p-2 rounded">
              ⚠️ All mappings must have both Source Field and Destination Column filled in
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setMappings([])}>
              Clear All
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving || mappings.some((m) => !m.sourceField || !m.destColumn)}
              className="px-6"
            >
              {isSaving ? 'Saving...' : 'Save Mappings'}
            </Button>
          </div>
        </div>
      )}

      {/* Validation Messages */}
      {mappings.length === 0 && fetchedFields.length > 0 && (
        <div className="text-sm text-amber-700 bg-amber-50 p-3 rounded flex items-center gap-2">
          <AlertCircle size={16} />
          At least one mapping is required to proceed
        </div>
      )}
    </div>
  )
}
