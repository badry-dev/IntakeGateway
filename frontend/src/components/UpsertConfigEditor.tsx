import { useState } from 'react'
import { Card, Select, Radio, Button, Input, Tag, Space, Typography, Alert, Checkbox } from 'antd'
import { PlusOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { OracleColumn, UpsertConfig } from '@/types'

const { Text } = Typography

interface UpsertConfigEditorProps {
  config: UpsertConfig
  availableColumns: OracleColumn[]
  onChange: (config: UpsertConfig) => void
  disabled?: boolean
}

export function UpsertConfigEditor({ config, availableColumns, onChange, disabled = false }: UpsertConfigEditorProps) {
  const [selectedKey, setSelectedKey] = useState<string>('')

  const addUpsertKey = () => {
    if (!selectedKey || config.upsert_keys?.includes(selectedKey)) return
    onChange({ ...config, upsert_keys: [...(config.upsert_keys || []), selectedKey] })
    setSelectedKey('')
  }

  const removeUpsertKey = (key: string) => {
    const newKeys = (config.upsert_keys || []).filter(k => k !== key)
    onChange({ ...config, upsert_keys: newKeys.length > 0 ? newKeys : undefined })
  }

  const availableForKey = availableColumns.filter(col => !config.upsert_keys?.includes(col.column_name))

  return (
    <Card title="Database Insert Options" extra={<Text type="secondary">Configure how records are inserted or updated</Text>}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Insert Mode */}
        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>Insert Mode</Text>
          <Radio.Group
            value={config.upsert_enabled ? 'upsert' : 'insert'}
            onChange={(e) => onChange({ ...config, upsert_enabled: e.target.value === 'upsert' })}
            disabled={disabled}
          >
            <Space direction="vertical">
              <Radio value="insert">Insert only (fail on duplicates)</Radio>
              <Radio value="upsert">Upsert (update if exists, insert if new)</Radio>
            </Space>
          </Radio.Group>
        </div>

        {/* Upsert Keys */}
        {config.upsert_enabled && (
          <Card size="small" style={{ background: '#fafafa' }}>
            <Text strong>Unique Key Columns</Text>
            <div style={{ marginBottom: 8 }}><Text type="secondary" style={{ fontSize: 12 }}>Select columns that uniquely identify a record</Text></div>

            <Space wrap style={{ marginBottom: 12 }}>
              {config.upsert_keys?.map(key => (
                <Tag
                  key={key}
                  closable={!disabled}
                  onClose={() => removeUpsertKey(key)}
                  color="blue"
                >
                  {key}
                </Tag>
              ))}
              {(!config.upsert_keys || config.upsert_keys.length === 0) && (
                <Text type="secondary" style={{ fontStyle: 'italic' }}>No keys selected</Text>
              )}
            </Space>

            <Space>
              <Select
                value={selectedKey || undefined}
                onChange={setSelectedKey}
                placeholder="Select a column..."
                disabled={disabled || availableForKey.length === 0}
                options={availableForKey.map(col => ({ value: col.column_name, label: `${col.column_name} (${col.data_type})` }))}
                style={{ width: 250 }}
              />
              <Button icon={<PlusOutlined />} onClick={addUpsertKey} disabled={disabled || !selectedKey} />
            </Space>

            <Alert
              message="Upsert keys should match unique or primary key constraints in the destination table"
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              style={{ marginTop: 12 }}
            />
          </Card>
        )}

        {/* Skip Already Processed */}
        {config.upsert_enabled && (
          <Card size="small" style={{ background: '#fafafa' }}>
            <Text strong>Skip Already Processed Records (Optional)</Text>
            <div style={{ marginBottom: 12 }}><Text type="secondary" style={{ fontSize: 12 }}>Skip rows where a specific column has a certain value</Text></div>

            <div style={{ display: 'flex', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <Text strong style={{ fontSize: 12 }}>Skip Column</Text>
                <Select
                  value={config.skip_column || undefined}
                  onChange={(v) => onChange({ ...config, skip_column: v || undefined })}
                  placeholder="Select column..."
                  disabled={disabled}
                  allowClear
                  options={[
                    ...availableColumns.map(col => ({ value: col.column_name, label: col.column_name })),
                  ]}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <Text strong style={{ fontSize: 12 }}>Skip Value</Text>
                <Input
                  value={config.skip_value || ''}
                  onChange={(e) => onChange({ ...config, skip_value: e.target.value || undefined })}
                  placeholder="e.g., Y"
                  disabled={disabled || !config.skip_column}
                />
              </div>
            </div>

            {config.skip_column && config.skip_value && (
              <Alert
                message={<>Rows where <strong>{config.skip_column}</strong> = "<strong>{config.skip_value}</strong>" will be skipped during import</>}
                type="info"
                showIcon
                icon={<InfoCircleOutlined />}
                style={{ marginTop: 12 }}
              />
            )}
          </Card>
        )}

        {/* Continue on Error */}
        <Checkbox
          checked={config.continue_on_error}
          onChange={(e) => onChange({ ...config, continue_on_error: e.target.checked })}
          disabled={disabled}
        >
          Continue on row errors (log and skip failed rows instead of stopping)
        </Checkbox>

        {!config.continue_on_error && (
          <Alert
            message="The import will stop immediately when a row error occurs. This may leave partial data in the destination table."
            type="error"
            showIcon
            icon={<WarningOutlined />}
          />
        )}
      </Space>
    </Card>
  )
}

export default UpsertConfigEditor
