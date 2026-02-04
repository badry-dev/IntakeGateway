import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Connection, ConnectionCreate, ConnectionUpdate, DatabaseType } from '@/types'
import { useTestConnection } from '@/hooks/api'
import { CheckCircle, XCircle, Loader2, Database, Server } from 'lucide-react'

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

export function ConnectionEditor({
  connection,
  onSave,
  onDelete,
  onCancel,
  isLoading = false,
}: ConnectionEditorProps) {
  const isEditing = !!connection

  // Form state
  const [name, setName] = useState(connection?.name || '')
  const [dbType, setDbType] = useState<DatabaseType>(connection?.db_type || 'oracle')
  const [host, setHost] = useState(connection?.host || '')
  const [port, setPort] = useState(connection?.port || 1521)
  const [username, setUsername] = useState(connection?.username || '')
  const [password, setPassword] = useState('')
  const [serviceName, setServiceName] = useState(connection?.service_name || '')
  const [database, setDatabase] = useState(connection?.database || '')

  // UI state
  const [isSaving, setIsSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms?: number; server_version?: string } | null>(null)

  const testConnection = useTestConnection()

  // Update port when DB type changes (only for new connections)
  useEffect(() => {
    if (!connection) {
      const dbOption = DB_TYPE_OPTIONS.find(o => o.value === dbType)
      if (dbOption) {
        setPort(dbOption.defaultPort)
      }
    }
  }, [dbType, connection])

  const handleTest = async () => {
    setTestResult(null)

    const testData = {
      db_type: dbType,
      host,
      port,
      username,
      password: password || (isEditing ? '' : ''),
      service_name: dbType === 'oracle' ? serviceName : undefined,
      database: dbType !== 'oracle' ? database : undefined,
    }

    // Can't test without password on new connections
    if (!isEditing && !password) {
      setTestResult({ success: false, message: 'Password is required to test connection' })
      return
    }

    // For editing without new password, inform user
    if (isEditing && !password) {
      setTestResult({ success: false, message: 'Enter password to test connection with new credentials' })
      return
    }

    try {
      const result = await testConnection.mutateAsync(testData)
      setTestResult({
        success: result.success,
        message: result.message,
        latency_ms: result.latency_ms,
        server_version: result.server_version,
      })
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || error.message || 'Test failed',
      })
    }
  }

  const handleSave = async () => {
    setIsSaving(true)

    try {
      const data: ConnectionCreate | ConnectionUpdate = {
        name,
        db_type: dbType,
        host,
        port,
        username,
        ...(password ? { password } : {}),
        service_name: dbType === 'oracle' ? serviceName : undefined,
        database: dbType !== 'oracle' ? database : undefined,
      }

      await onSave(data)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!onDelete) return
    setIsSaving(true)
    try {
      await onDelete()
    } finally {
      setIsSaving(false)
      setDeleteConfirm(false)
    }
  }

  // Validation: require all fields, and password for new connections
  const isValid =
    name &&
    host &&
    username &&
    (isEditing || password) &&
    (dbType === 'oracle' ? serviceName : database)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          {isEditing ? 'Edit Connection' : 'New Connection'}
        </CardTitle>
        <CardDescription>
          {isEditing
            ? 'Update database connection settings'
            : 'Configure a new database connection'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Connection Name */}
        <div className="space-y-2">
          <Label htmlFor="name">Connection Name</Label>
          <Input
            id="name"
            placeholder="e.g., Production Database"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isLoading || isSaving}
          />
        </div>

        {/* Database Type */}
        <div className="space-y-2">
          <Label htmlFor="db_type">Database Type</Label>
          <Select
            value={dbType}
            onValueChange={(v) => setDbType(v as DatabaseType)}
            disabled={isLoading || isSaving || isEditing}
          >
            <SelectTrigger id="db_type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DB_TYPE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {isEditing && (
            <p className="text-xs text-muted-foreground">
              Database type cannot be changed after creation
            </p>
          )}
        </div>

        {/* Host and Port */}
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 space-y-2">
            <Label htmlFor="host">Host</Label>
            <Input
              id="host"
              placeholder="e.g., db.example.com"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="port">Port</Label>
            <Input
              id="port"
              type="number"
              value={port}
              onChange={(e) => setPort(parseInt(e.target.value) || 1521)}
              disabled={isLoading || isSaving}
            />
          </div>
        </div>

        {/* Service Name (Oracle) or Database (PG/MySQL) */}
        {dbType === 'oracle' ? (
          <div className="space-y-2">
            <Label htmlFor="service_name">Service Name</Label>
            <Input
              id="service_name"
              placeholder="e.g., ORCL"
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="database">Database</Label>
            <Input
              id="database"
              placeholder="e.g., myapp"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
        )}

        {/* Credentials */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              placeholder="Database username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">
              Password{' '}
              {isEditing && (
                <span className="text-muted-foreground font-normal">
                  (leave blank to keep current)
                </span>
              )}
            </Label>
            <Input
              id="password"
              type="password"
              placeholder={isEditing ? '********' : 'Database password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
        </div>

        {/* Test Result */}
        {testResult && (
          <div
            className={`flex items-start gap-2 p-3 rounded-md ${
              testResult.success
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}
          >
            {testResult.success ? (
              <CheckCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            ) : (
              <XCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            )}
            <div className="flex-1 text-sm">
              <p>{testResult.message}</p>
              {testResult.success && testResult.latency_ms && (
                <p className="mt-1 text-green-600">
                  Latency: {testResult.latency_ms}ms
                  {testResult.server_version && (
                    <span className="ml-2">| Version: {testResult.server_version}</span>
                  )}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-4 border-t">
          <Button
            variant="outline"
            onClick={handleTest}
            disabled={isLoading || isSaving || !host || !username}
          >
            {testConnection.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Server className="h-4 w-4 mr-2" />
                Test Connection
              </>
            )}
          </Button>

          <div className="flex-1" />

          {onCancel && (
            <Button variant="ghost" onClick={onCancel} disabled={isSaving}>
              Cancel
            </Button>
          )}

          {isEditing && onDelete && !deleteConfirm && (
            <Button
              variant="outline"
              onClick={() => setDeleteConfirm(true)}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
              disabled={isSaving}
            >
              Delete
            </Button>
          )}

          {deleteConfirm && (
            <>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={isSaving}
              >
                {isSaving ? 'Deleting...' : 'Confirm Delete'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => setDeleteConfirm(false)}
                disabled={isSaving}
              >
                Cancel
              </Button>
            </>
          )}

          {!deleteConfirm && (
            <Button onClick={handleSave} disabled={!isValid || isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : isEditing ? (
                'Update'
              ) : (
                'Create'
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
