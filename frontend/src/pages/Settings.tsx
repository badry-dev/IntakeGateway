import { useState } from 'react'
import { Card, Table, Tag, Button, Tabs, Modal, Space, Typography, Empty, Spin, Alert, message } from 'antd'
import {
  DatabaseOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  EditOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
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

const { Title, Text } = Typography

export function Settings() {
  const [editingConnection, setEditingConnection] = useState<Connection | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const { data: connectionsData, isLoading, isError, error } = useConnections()
  const createConnection = useCreateConnection(() => { setShowCreateDialog(false); message.success('Connection created') })
  const updateConnection = useUpdateConnection(() => { setEditingConnection(null); message.success('Connection updated') })
  const deleteConnection = useDeleteConnection(() => { setEditingConnection(null); message.success('Connection deleted') })
  const activateConnection = useActivateConnection()

  const connections = connectionsData?.connections || []
  const activeConnectionId = connectionsData?.active_connection_id

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name', render: (v: string) => <Text strong>{v}</Text> },
    {
      title: 'Type',
      dataIndex: 'db_type',
      key: 'db_type',
      render: (v: string) => <Tag>{v.toUpperCase()}</Tag>,
    },
    {
      title: 'Host',
      key: 'host',
      render: (_: unknown, record: Connection) => <Text code>{record.host}:{record.port}</Text>,
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, record: Connection) =>
        record.id === activeConnectionId ? (
          <Tag icon={<CheckCircleOutlined />} color="success">Active</Tag>
        ) : (
          <Button
            size="small"
            onClick={() => {
              activateConnection.mutateAsync(record.id)
                .then(() => message.success('Connection activated'))
                .catch(() => message.error('Failed to activate connection'))
            }}
            loading={activateConnection.isPending}
          >
            Set Active
          </Button>
        ),
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (v: string) => format(new Date(v), 'MMM d, yyyy'),
    },
    {
      title: 'Actions',
      key: 'actions',
      align: 'right' as const,
      render: (_: unknown, record: Connection) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => setEditingConnection(record)} />
      ),
    },
  ]

  const tabItems = [
    {
      key: 'connections',
      label: <span><DatabaseOutlined /> Database Connections</span>,
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Title level={4} style={{ margin: 0 }}>Database Connections</Title>
              <Text type="secondary">Manage database connections for data import tasks</Text>
            </div>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowCreateDialog(true)}>
              Add Connection
            </Button>
          </div>

          {isLoading && (
            <Card><div style={{ textAlign: 'center', padding: 48 }}><Spin indicator={<LoadingOutlined />} size="large" /><br /><Text type="secondary">Loading connections...</Text></div></Card>
          )}

          {isError && (
            <Alert
              message="Failed to load connections"
              description={(error as any)?.message || 'An error occurred'}
              type="error"
              showIcon
              icon={<ExclamationCircleOutlined />}
            />
          )}

          {!isLoading && !isError && connections.length === 0 && (
            <Card>
              <Empty
                image={<DatabaseOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
                description={<><Text type="secondary">No database connections configured</Text><br /><Text type="secondary" style={{ fontSize: 12 }}>The application is using environment variables for database connection.</Text></>}
              >
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowCreateDialog(true)}>
                  Add Your First Connection
                </Button>
              </Empty>
            </Card>
          )}

          {!isLoading && !isError && connections.length > 0 && (
            <Card>
              <Table columns={columns} dataSource={connections} rowKey="id" pagination={false} />
            </Card>
          )}

          <Alert
            message="Note"
            description="If no connections are configured, the application will use environment variables (ORACLE_HOST, ORACLE_USER, etc.) as a fallback. The active connection is used by default for all tasks."
            type="info"
            showIcon
          />
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ margin: 0 }}><SettingOutlined /> Settings</Title>
        <Text type="secondary">Manage application configuration</Text>
      </div>

      <Tabs items={tabItems} />

      {/* Create Connection Modal */}
      <Modal
        title="New Connection"
        open={showCreateDialog}
        onCancel={() => setShowCreateDialog(false)}
        footer={null}
        width={700}
        destroyOnClose
      >
        <ConnectionEditor
          onSave={async (data) => { await createConnection.mutateAsync(data as ConnectionCreate) }}
          onCancel={() => setShowCreateDialog(false)}
          isLoading={createConnection.isPending}
        />
      </Modal>

      {/* Edit Connection Modal */}
      <Modal
        title="Edit Connection"
        open={!!editingConnection}
        onCancel={() => setEditingConnection(null)}
        footer={null}
        width={700}
        destroyOnClose
      >
        {editingConnection && (
          <ConnectionEditor
            connection={editingConnection}
            onSave={async (data) => {
              await updateConnection.mutateAsync({ id: editingConnection.id, data: data as ConnectionUpdate })
            }}
            onDelete={async () => {
              await deleteConnection.mutateAsync(editingConnection.id)
            }}
            onCancel={() => setEditingConnection(null)}
            isLoading={updateConnection.isPending || deleteConnection.isPending}
          />
        )}
      </Modal>
    </Space>
  )
}
