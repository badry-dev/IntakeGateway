import { useState, useEffect } from 'react'
import { Button, Input, Select, Space, Typography, Alert, InputNumber, Divider } from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { Connection, ConnectionCreate, ConnectionUpdate, DatabaseType } from '@/types'
import { useTestConnection } from '@/hooks/api'

const { Text } = Typography

interface ConnectionEditorProps {
  connection?: Connection
  onSave: (data: ConnectionCreate | ConnectionUpdate) => Promise<void>
  onDelete?: () => Promise<void>
  onCancel?: () => void
  isLoading?: boolean
}

const DB_TYPE_OPTIONS: { value: DatabaseType; label: string; defaultPort: number }[] = [
  { value: 'oracle', label: 'Oracle', defaultPort: 1521 },
  { value: 'postgresql', label: 'PostgreSQL', defaultPort: 5432 },
  { value: 'mysql', label: 'MySQL', defaultPort: 3306 },
]

export function ConnectionEditor({ connection, onSave, onDelete, onCancel, isLoading = false }: ConnectionEditorProps) {
  const isEditing = !!connection

  const [name, setName] = useState(connection?.name || '')
  const [dbType, setDbType] = useState<DatabaseType>(connection?.db_type || 'oracle')
  const [host, setHost] = useState(connection?.host || '')
  const [port, setPort] = useState(connection?.port || 1521)
  const [username, setUsername] = useState(connection?.username || '')
  const [password, setPassword] = useState('')
  const [serviceName, setServiceName] = useState(connection?.service_name || '')
  const [database, setDatabase] = useState(connection?.database || '')

  const [isSaving, setIsSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms?: number; server_version?: string } | null>(null)

  const testConnection = useTestConnection()

  useEffect(() => {
    if (!connection) {
      const dbOption = DB_TYPE_OPTIONS.find(o => o.value === dbType)
      if (dbOption) setPort(dbOption.defaultPort)
    }
  }, [dbType, connection])

  const handleTest = async () => {
    setTestResult(null)
    if (!isEditing && !password) { setTestResult({ success: false, message: 'Password is required' }); return }
    if (isEditing && !password) { setTestResult({ success: false, message: 'Enter password to test' }); return }
    try {
      const result = await testConnection.mutateAsync({
        db_type: dbType, host, port, username, password,
        service_name: dbType === 'oracle' ? serviceName : undefined,
        database: dbType !== 'oracle' ? database : undefined,
      })
      setTestResult({ success: result.success, message: result.message, latency_ms: result.latency_ms, server_version: result.server_version })
    } catch (error: any) {
      setTestResult({ success: false, message: error.response?.data?.detail || error.message || 'Test failed' })
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onSave({
        name, db_type: dbType, host, port, username,
        ...(password ? { password } : {}),
        service_name: dbType === 'oracle' ? serviceName : undefined,
        database: dbType !== 'oracle' ? database : undefined,
      })
    } finally { setIsSaving(false) }
  }

  const handleDelete = async () => {
    if (!onDelete) return
    setIsSaving(true)
    try { await onDelete() } finally { setIsSaving(false); setDeleteConfirm(false) }
  }

  const isValid = name && host && username && (isEditing || password) && (dbType === 'oracle' ? serviceName : database)

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div>
        <Text strong>Connection Name</Text>
        <Input placeholder="e.g., Production Database" value={name} onChange={(e) => setName(e.target.value)} disabled={isLoading || isSaving} />
      </div>

      <div>
        <Text strong>Database Type</Text>
        <Select
          value={dbType} onChange={(v) => setDbType(v)} disabled={isLoading || isSaving || isEditing}
          options={DB_TYPE_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
          style={{ width: '100%' }}
        />
        {isEditing && <Text type="secondary" style={{ fontSize: 12 }}>Database type cannot be changed after creation</Text>}
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: 2 }}>
          <Text strong>Host</Text>
          <Input placeholder="e.g., db.example.com" value={host} onChange={(e) => setHost(e.target.value)} disabled={isLoading || isSaving} />
        </div>
        <div style={{ flex: 1 }}>
          <Text strong>Port</Text>
          <InputNumber value={port} onChange={(v) => setPort(v || 1521)} disabled={isLoading || isSaving} style={{ width: '100%' }} />
        </div>
      </div>

      {dbType === 'oracle' ? (
        <div>
          <Text strong>Service Name</Text>
          <Input placeholder="e.g., ORCL" value={serviceName} onChange={(e) => setServiceName(e.target.value)} disabled={isLoading || isSaving} />
        </div>
      ) : (
        <div>
          <Text strong>Database</Text>
          <Input placeholder="e.g., myapp" value={database} onChange={(e) => setDatabase(e.target.value)} disabled={isLoading || isSaving} />
        </div>
      )}

      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <Text strong>Username</Text>
          <Input placeholder="Database username" value={username} onChange={(e) => setUsername(e.target.value)} disabled={isLoading || isSaving} />
        </div>
        <div style={{ flex: 1 }}>
          <Text strong>Password {isEditing && <Text type="secondary" style={{ fontWeight: 'normal' }}>(leave blank to keep current)</Text>}</Text>
          <Input.Password placeholder={isEditing ? '********' : 'Database password'} value={password} onChange={(e) => setPassword(e.target.value)} disabled={isLoading || isSaving} />
        </div>
      </div>

      {testResult && (
        <Alert
          message={testResult.message}
          description={testResult.success && testResult.latency_ms ? `Latency: ${testResult.latency_ms}ms${testResult.server_version ? ` | Version: ${testResult.server_version}` : ''}` : undefined}
          type={testResult.success ? 'success' : 'error'}
          showIcon
          icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
        />
      )}

      <Divider style={{ margin: '8px 0' }} />

      <Space style={{ width: '100%', justifyContent: 'space-between', display: 'flex' }}>
        <Button icon={<ApiOutlined />} onClick={handleTest} disabled={isLoading || isSaving || !host || !username} loading={testConnection.isPending}>
          Test Connection
        </Button>

        <Space>
          {onCancel && <Button onClick={onCancel} disabled={isSaving}>Cancel</Button>}
          {isEditing && onDelete && !deleteConfirm && (
            <Button danger onClick={() => setDeleteConfirm(true)} disabled={isSaving}>Delete</Button>
          )}
          {deleteConfirm && (
            <>
              <Button type="primary" danger onClick={handleDelete} loading={isSaving}>Confirm Delete</Button>
              <Button onClick={() => setDeleteConfirm(false)} disabled={isSaving}>Cancel</Button>
            </>
          )}
          {!deleteConfirm && (
            <Button type="primary" onClick={handleSave} disabled={!isValid || isSaving} loading={isSaving}>
              {isEditing ? 'Update' : 'Create'}
            </Button>
          )}
        </Space>
      </Space>
    </Space>
  )
}
