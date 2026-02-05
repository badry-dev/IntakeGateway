import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { OracleColumn, UpsertConfig } from '@/types'
import { AlertTriangle, Info, Plus, X } from 'lucide-react'

interface UpsertConfigEditorProps {
  config: UpsertConfig
  availableColumns: OracleColumn[]
  onChange: (config: UpsertConfig) => void
  disabled?: boolean
}

export function UpsertConfigEditor({
  config,
  availableColumns,
  onChange,
  disabled = false,
}: UpsertConfigEditorProps) {
  const [selectedKey, setSelectedKey] = useState<string>('')

  // Add a new upsert key
  const addUpsertKey = () => {
    // If nothing is selected, do nothing.
    if (!selectedKey) return

    // If the key is already selected, inform the user and do not add it again.
    if (config.upsert_keys?.includes(selectedKey)) {
      window.alert('This column is already configured as an upsert key.')
      return
    }
    const newKeys = [...(config.upsert_keys || []), selectedKey]
    onChange({ ...config, upsert_keys: newKeys })
    setSelectedKey('')
  }

  // Remove an upsert key
  const removeUpsertKey = (key: string) => {
    const newKeys = (config.upsert_keys || []).filter(k => k !== key)
    onChange({ ...config, upsert_keys: newKeys.length > 0 ? newKeys : undefined })
  }

  // Get available columns for key selection (exclude already selected)
  const availableForKey = availableColumns.filter(
    col => !config.upsert_keys?.includes(col.column_name)
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Database Insert Options</CardTitle>
        <CardDescription>
          Configure how records are inserted or updated in the destination table
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Insert Mode Selection */}
        <div className="space-y-3">
          <Label className="text-base font-medium">Insert Mode</Label>
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="insert-only"
                name="insert-mode"
                checked={!config.upsert_enabled}
                onChange={() => onChange({ ...config, upsert_enabled: false })}
                disabled={disabled}
                className="h-4 w-4"
              />
              <Label htmlFor="insert-only" className="font-normal cursor-pointer">
                Insert only (fail on duplicates)
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="upsert"
                name="insert-mode"
                checked={config.upsert_enabled}
                onChange={() => onChange({ ...config, upsert_enabled: true })}
                disabled={disabled}
                className="h-4 w-4"
              />
              <Label htmlFor="upsert" className="font-normal cursor-pointer">
                Upsert (update if exists, insert if new)
              </Label>
            </div>
          </div>
        </div>

        {/* Upsert Key Columns - only shown when upsert is enabled */}
        {config.upsert_enabled && (
          <div className="space-y-3 p-4 bg-slate-50 rounded-lg">
            <Label className="text-base font-medium">Unique Key Columns</Label>
            <p className="text-sm text-slate-600">
              Select columns that uniquely identify a record for matching
            </p>

            {/* Selected keys */}
            <div className="flex flex-wrap gap-2 min-h-[40px]">
              {config.upsert_keys?.map(key => (
                <div
                  key={key}
                  className="flex items-center gap-1 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                >
                  <span>{key}</span>
                  <button
                    onClick={() => removeUpsertKey(key)}
                    disabled={disabled}
                    className="hover:bg-blue-200 rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
              {(!config.upsert_keys || config.upsert_keys.length === 0) && (
                <span className="text-sm text-slate-400 italic">No keys selected</span>
              )}
            </div>

            {/* Add key selector */}
            <div className="flex gap-2">
              <Select
                value={selectedKey}
                onValueChange={setSelectedKey}
                disabled={disabled || availableForKey.length === 0}
              >
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Select a column..." />
                </SelectTrigger>
                <SelectContent>
                  {availableForKey.map(col => (
                    <SelectItem key={col.column_name} value={col.column_name}>
                      {col.column_name} ({col.data_type})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={addUpsertKey}
                disabled={disabled || !selectedKey}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            {/* Warning about upsert keys */}
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-amber-800">
                Upsert keys should match unique or primary key constraints in the destination table
              </p>
            </div>
          </div>
        )}

        {/* Skip Already Processed Records - only shown when upsert is enabled */}
        {config.upsert_enabled && (
          <div className="space-y-3 p-4 bg-slate-50 rounded-lg">
            <Label className="text-base font-medium">Skip Already Processed Records (Optional)</Label>
            <p className="text-sm text-slate-600">
              Skip rows where a specific column has a certain value (useful when third-party systems mark records as processed)
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="skip-column">Skip Column</Label>
                <Select
                  value={config.skip_column || ''}
                  onValueChange={(value) => onChange({ ...config, skip_column: value || undefined })}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select column..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
                    {availableColumns.map(col => (
                      <SelectItem key={col.column_name} value={col.column_name}>
                        {col.column_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="skip-value">Skip Value</Label>
                <Input
                  id="skip-value"
                  value={config.skip_value || ''}
                  onChange={(e) => onChange({ ...config, skip_value: e.target.value || undefined })}
                  placeholder="e.g., Y"
                  disabled={disabled || !config.skip_column}
                />
              </div>
            </div>

            {config.skip_column && config.skip_value && (
              <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-blue-800">
                  Rows where <strong>{config.skip_column}</strong> = "<strong>{config.skip_value}</strong>" will be skipped during import
                </p>
              </div>
            )}
          </div>
        )}

        {/* Continue on Error */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="continue-on-error"
            checked={config.continue_on_error}
            onCheckedChange={(checked) => onChange({ ...config, continue_on_error: checked === true })}
            disabled={disabled}
          />
          <Label htmlFor="continue-on-error" className="font-normal cursor-pointer">
            Continue on row errors (log and skip failed rows instead of stopping)
          </Label>
        </div>

        {!config.continue_on_error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
            <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-800">
              The import will stop immediately when a row error occurs. This may leave partial data in the destination table.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default UpsertConfigEditor
