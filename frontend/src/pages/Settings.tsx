import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { ConnectionEditor } from '@/components/ConnectionEditor'
import {
  useConnections,
  useCreateConnection,
  useUpdateConnection,
  useDeleteConnection,
  useActivateConnection,
} from '@/hooks/api'
import { Connection, ConnectionCreate, ConnectionUpdate } from '@/types'
import { format } from 'date-fns'
import {
  Database,
  PlusIcon,
  CheckCircle,
  Settings as SettingsIcon,
  Pencil,
  Loader2,
  AlertCircle,
} from 'lucide-react'

export function Settings() {
  const [activeTab, setActiveTab] = useState('connections')
  const [editingConnection, setEditingConnection] = useState<Connection | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const { data: connectionsData, isLoading, isError, error } = useConnections()
  const createConnection = useCreateConnection(() => setShowCreateDialog(false))
  const updateConnection = useUpdateConnection(() => setEditingConnection(null))
  const deleteConnection = useDeleteConnection(() => setEditingConnection(null))
  const activateConnection = useActivateConnection()

  const connections = connectionsData?.connections || []
  const activeConnectionId = connectionsData?.active_connection_id

  const handleCreate = async (data: ConnectionCreate | ConnectionUpdate) => {
    await createConnection.mutateAsync(data as ConnectionCreate)
  }

  const handleUpdate = async (data: ConnectionCreate | ConnectionUpdate) => {
    if (editingConnection) {
      await updateConnection.mutateAsync({
        id: editingConnection.id,
        data: data as ConnectionUpdate,
      })
    }
  }

  const handleDelete = async () => {
    if (editingConnection) {
      await deleteConnection.mutateAsync(editingConnection.id)
    }
  }

  const handleActivate = async (id: string) => {
    await activateConnection.mutateAsync(id)
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <SettingsIcon className="h-8 w-8" />
          Settings
        </h1>
        <p className="text-muted-foreground">Manage application configuration</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="connections" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Database Connections
          </TabsTrigger>
        </TabsList>

        <TabsContent value="connections" className="space-y-4 mt-4">
          {/* Header with Create Button */}
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Database Connections</h2>
              <p className="text-sm text-muted-foreground">
                Manage database connections for data import tasks
              </p>
            </div>

            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <Button onClick={() => setShowCreateDialog(true)}>
                <PlusIcon className="h-4 w-4 mr-2" />
                Add Connection
              </Button>
              <DialogContent className="max-w-2xl">
                <ConnectionEditor
                  onSave={handleCreate}
                  onCancel={() => setShowCreateDialog(false)}
                  isLoading={createConnection.isPending}
                />
              </DialogContent>
            </Dialog>
          </div>

          {/* Loading State */}
          {isLoading && (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Loading connections...</p>
              </CardContent>
            </Card>
          )}

          {/* Error State */}
          {isError && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="py-6 flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-red-600" />
                <div>
                  <p className="text-red-800 font-medium">Failed to load connections</p>
                  <p className="text-red-600 text-sm">
                    {(error as any)?.message || 'An error occurred'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Empty State */}
          {!isLoading && !isError && connections.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center">
                <Database className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">
                  No database connections configured
                </p>
                <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
                  The application is using environment variables for database connection.
                  Add a connection to manage multiple databases through the UI.
                </p>
                <Button onClick={() => setShowCreateDialog(true)}>
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Add Your First Connection
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Connection List */}
          {!isLoading && !isError && connections.length > 0 && (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Host</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {connections.map((conn) => (
                    <TableRow key={conn.id}>
                      <TableCell className="font-medium">{conn.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {conn.db_type.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {conn.host}:{conn.port}
                      </TableCell>
                      <TableCell>
                        {conn.id === activeConnectionId ? (
                          <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Active
                          </Badge>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleActivate(conn.id)}
                            disabled={activateConnection.isPending}
                          >
                            {activateConnection.isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              'Set Active'
                            )}
                          </Button>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(conn.updated_at), 'MMM d, yyyy')}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingConnection(conn)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}

          {/* Info Card */}
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="py-4">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> If no connections are configured, the application
                will use environment variables (ORACLE_HOST, ORACLE_USER, etc.) as a
                fallback. The active connection is used by default for all tasks.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog */}
      <Dialog
        open={!!editingConnection}
        onOpenChange={(open) => !open && setEditingConnection(null)}
      >
        <DialogContent className="max-w-2xl">
          {editingConnection && (
            <ConnectionEditor
              connection={editingConnection}
              onSave={handleUpdate}
              onDelete={handleDelete}
              onCancel={() => setEditingConnection(null)}
              isLoading={
                updateConnection.isPending || deleteConnection.isPending
              }
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
