import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useTask,
  useConnections,
  useUpdateTask,
  useDeleteTask,
  useColumnMappings,
  useSchedule,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useBackfillTask,
} from '@/hooks/api'
import {
  Card,
  Button,
  Input,
  Tabs,
  Tag,
  Space,
  Typography,
  Modal,
  Spin,
  Descriptions,
  message,
  Switch,
  Alert,
  Divider,
} from 'antd'
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { TaskFormData, ScheduleCreate, ApiErrorLike } from '@/types'

// Narrow an `unknown` error to ApiErrorLike before reading axios fields.
function isApiErrorLike(e: unknown): e is ApiErrorLike {
  return (
    typeof e === 'object' &&
    e !== null &&
    'response' in e &&
    typeof (e as { response?: unknown }).response === 'object'
  )
}
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'
import { ScheduleEditor } from '@/components/ScheduleEditor'
import { Select } from 'antd'

const { Text } = Typography

export function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: task, isLoading, error } = useTask(Number(id) || 0)
  const { data: connectionsData } = useConnections()
  const updateTaskMutation = useUpdateTask()
  const deleteTaskMutation = useDeleteTask()
  const { data: mappings } = useColumnMappings(Number(id) || 0)
  const { data: schedule, refetch: refetchSchedule } = useSchedule(Number(id) || 0)
  const createScheduleMutation = useCreateSchedule()
  const updateScheduleMutation = useUpdateSchedule()
  const deleteScheduleMutation = useDeleteSchedule()

  const [isEditOpen, setIsEditOpen] = useState(false)
  const [formData, setFormData] = useState<TaskFormData>({
    name: '', description: '', endpoint_path: '', http_method: 'GET',
    dest_table: '', headers_json: {}, body_json: {}, batch_size: 500, is_active: true, connection_id: '',
  })

  // Upsert configuration state
  const [upsertEnabled, setUpsertEnabled] = useState(false)
  const [upsertKeys, setUpsertKeys] = useState<string[]>([])
  const [skipColumn, setSkipColumn] = useState('')
  const [skipValue, setSkipValue] = useState('')
  const [upsertKeyInput, setUpsertKeyInput] = useState('')

  // Backfill modal state (P0-C)
  const backfillMutation = useBackfillTask()
  const [isBackfillOpen, setIsBackfillOpen] = useState(false)
  const [backfillStart, setBackfillStart] = useState('')
  const [backfillEnd, setBackfillEnd] = useState('')

  const connections = connectionsData?.connections || []
  const selectedConnection = connectionsData?.connections.find(
    (connection) => connection.id === task?.connection_id
  )

  React.useEffect(() => {
    if (task) {
      setFormData({
        name: task.name, description: task.description || '', endpoint_path: task.endpoint_path,
        http_method: task.http_method as any, dest_table: task.dest_table,
        headers_json: task.headers_json || {}, body_json: task.body_json || {},
        batch_size: task.batch_size, is_active: task.is_active, connection_id: task.connection_id || '',
      })
      // Initialize upsert settings
      setUpsertEnabled(task.upsert_enabled || false)
      setUpsertKeys(task.upsert_keys || [])
      setSkipColumn(task.skip_column || '')
      setSkipValue(task.skip_value || '')
    }
  }, [task])

  if (isLoading) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')} style={{ marginBottom: 16 }}>Back to Tasks</Button>
        <Spin tip="Loading task details..." size="large"><div style={{ padding: 50 }} /></Spin>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')} style={{ marginBottom: 16 }}>Back to Tasks</Button>
        <Card><Text type="danger">Error loading task: {error?.message || 'Task not found'}</Text></Card>
      </div>
    )
  }

  const handleSaveEdit = async () => {
    if (!formData.connection_id) {
      message.error('Destination connection is required')
      return
    }

    try {
      await updateTaskMutation.mutateAsync({ id: task.id, data: formData })
      setIsEditOpen(false)
      message.success('Task updated')
    } catch {
      message.error('Failed to update task')
    }
  }

  const handleDelete = () => {
    Modal.confirm({
      title: 'Delete Task',
      content: `Are you sure you want to delete "${task.name}"? This will remove the task and all associated run history.`,
      okText: 'Delete', okType: 'danger',
      onOk: async () => {
        try {
          await deleteTaskMutation.mutateAsync(task.id)
          navigate('/tasks')
        } catch {
          message.error('Failed to delete task')
        }
      },
    })
  }

  const handleCreateSchedule = async (data: ScheduleCreate) => {
    await createScheduleMutation.mutateAsync({ taskId: Number(id), data })
    await refetchSchedule()
  }

  const handleUpdateSchedule = async (data: ScheduleCreate) => {
    if (!schedule) return
    await updateScheduleMutation.mutateAsync({ scheduleId: schedule.id, data })
    await refetchSchedule()
  }

  const handleDeleteSchedule = async () => {
    if (!schedule) return
    await deleteScheduleMutation.mutateAsync(schedule.id)
    await refetchSchedule()
  }

  const handleSaveUpsert = async () => {
    try {
      await updateTaskMutation.mutateAsync({
        id: task.id,
        data: {
          ...formData,
          upsert_enabled: upsertEnabled,
          upsert_keys: upsertKeys.length > 0 ? upsertKeys : undefined,
          skip_column: skipColumn.trim() || undefined,
          skip_value: skipValue.trim() || undefined,
        },
      })
      message.success('Upsert settings updated')
    } catch {
      message.error('Failed to update upsert settings')
    }
  }

  const handleAddUpsertKey = () => {
    const trimmed = upsertKeyInput.trim()
    if (trimmed && !upsertKeys.includes(trimmed)) {
      setUpsertKeys([...upsertKeys, trimmed])
      setUpsertKeyInput('')
    }
  }

  const handleRemoveUpsertKey = (key: string) => {
    setUpsertKeys(upsertKeys.filter((k) => k !== key))
  }

  const handleBackfill = async () => {
    if (!backfillStart.trim()) {
      message.warning('cursor_start is required for backfill')
      return
    }
    try {
      await backfillMutation.mutateAsync({
        taskId: task.id,
        cursorStart: backfillStart.trim(),
        cursorEnd: backfillEnd.trim() || undefined,
      })
      message.success('Backfill enqueued')
      setIsBackfillOpen(false)
      setBackfillStart('')
      setBackfillEnd('')
    } catch (e: unknown) {
      const detail =
        (isApiErrorLike(e) && e.response?.data?.detail) || 'Failed to enqueue backfill'
      message.error(detail)
    }
  }

  const tabItems = [
    {
      key: 'details',
      label: <span><SettingOutlined /> Task Details</span>,
      children: (
        <Card>
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="Name">{task.name}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={task.is_active ? 'green' : 'default'}>{task.is_active ? 'Active' : 'Inactive'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="HTTP Method"><Text code>{task.http_method}</Text></Descriptions.Item>
            <Descriptions.Item label="Destination Table"><Text code>{task.dest_table}</Text></Descriptions.Item>
            <Descriptions.Item label="Destination Connection">
              {selectedConnection?.name || 'Not configured'}
            </Descriptions.Item>
            <Descriptions.Item label="Endpoint URL" span={2}>
              <Space>
                <Text code copyable style={{ wordBreak: 'break-all' }}>{task.endpoint_path}</Text>
              </Space>
            </Descriptions.Item>
            {task.description && (
              <Descriptions.Item label="Description" span={2}>{task.description}</Descriptions.Item>
            )}
            <Descriptions.Item label="Created">
              {task.created_at ? new Date(task.created_at).toLocaleString() : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Batch Size">{task.batch_size}</Descriptions.Item>
          </Descriptions>

          {Object.keys(task.headers_json || {}).length > 0 && (
            <Card size="small" title="Headers" style={{ marginTop: 16 }}>
              {Object.entries(task.headers_json || {}).map(([key, value]) => (
                <div key={key}><Text code>{key}</Text>: <Text>{String(value)}</Text></div>
              ))}
            </Card>
          )}

          {Object.keys(task.body_json || {}).length > 0 && (
            <Card size="small" title="Request Body" style={{ marginTop: 16 }}>
              <pre style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(task.body_json, null, 2)}</pre>
            </Card>
          )}
        </Card>
      ),
    },
    {
      key: 'schedule',
      label: (
        <span>
          <ClockCircleOutlined /> Schedule
          {schedule && <Tag color="green" style={{ marginLeft: 8 }}>Active</Tag>}
        </span>
      ),
      children: (
        <Card title="Task Schedule" extra={<Text type="secondary">Configure automated execution</Text>}>
          <ScheduleEditor
            taskId={Number(id)}
            schedule={schedule || undefined}
            onSave={schedule ? handleUpdateSchedule : handleCreateSchedule}
            onDelete={schedule ? handleDeleteSchedule : undefined}
            isEditing={!!schedule}
          />
        </Card>
      ),
    },
    {
      key: 'mappings',
      label: (
        <span>
          <DatabaseOutlined /> Column Mappings
          {mappings && mappings.length > 0 && <Tag style={{ marginLeft: 8 }}>{mappings.length}</Tag>}
        </span>
      ),
      children: (
        <Card title="Column Mapping Configuration" extra={<Text type="secondary">Map API response fields to database columns</Text>}>
          <ColumnMappingEditor
            taskId={Number(id)}
            taskFormData={formData}
            existingMappings={mappings || []}
          />
        </Card>
      ),
    },
    {
      key: 'upsert',
      label: (
        <span>
          <SafetyOutlined /> Upsert Settings
          {upsertEnabled && <Tag color="blue" style={{ marginLeft: 8 }}>Enabled</Tag>}
        </span>
      ),
      children: (
        <Card
          title="Upsert Configuration"
          extra={
            <Button type="primary" onClick={handleSaveUpsert} loading={updateTaskMutation.isPending}>
              Save Upsert Settings
            </Button>
          }
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Alert
              message="Upsert Mode"
              description="When enabled, existing records will be updated instead of causing duplicate key errors. Requires unique key columns to match records."
              type="info"
              showIcon
            />

            <div>
              <Space align="center">
                <Text strong>Enable Upsert:</Text>
                <Switch checked={upsertEnabled} onChange={setUpsertEnabled} />
                <Text type="secondary">
                  {upsertEnabled ? 'Update existing records' : 'Insert only (fail on duplicates)'}
                </Text>
              </Space>
            </div>

            {upsertEnabled && (
              <>
                <Divider />

                <div>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>
                    Unique Key Columns *
                  </Text>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    Columns used to match existing records (e.g., REC_ID, EMPLOYEE_ID)
                  </Text>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space.Compact style={{ width: '100%' }}>
                      <Input
                        placeholder="Enter column name"
                        value={upsertKeyInput}
                        onChange={(e) => setUpsertKeyInput(e.target.value)}
                        onPressEnter={handleAddUpsertKey}
                      />
                      <Button type="primary" onClick={handleAddUpsertKey}>
                        Add Key
                      </Button>
                    </Space.Compact>
                    {upsertKeys.length > 0 && (
                      <Space wrap>
                        {upsertKeys.map((key) => (
                          <Tag
                            key={key}
                            closable
                            onClose={() => handleRemoveUpsertKey(key)}
                            color="blue"
                          >
                            {key}
                          </Tag>
                        ))}
                      </Space>
                    )}
                    {upsertKeys.length === 0 && (
                      <Alert
                        message="At least one unique key column is required for upsert mode"
                        type="warning"
                        showIcon
                      />
                    )}
                  </Space>
                </div>

                <Divider />

                <div>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>
                    Skip Already Processed Records (Optional)
                  </Text>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    Skip records where a specific column equals a certain value (e.g., processed='Y')
                  </Text>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text>Skip Column:</Text>
                      <Input
                        placeholder="e.g., processed"
                        value={skipColumn}
                        onChange={(e) => setSkipColumn(e.target.value)}
                        style={{ marginTop: 4 }}
                      />
                    </div>
                    <div>
                      <Text>Skip Value:</Text>
                      <Input
                        placeholder="e.g., Y"
                        value={skipValue}
                        onChange={(e) => setSkipValue(e.target.value)}
                        style={{ marginTop: 4 }}
                      />
                    </div>
                    {skipColumn && skipValue && (
                      <Alert
                        message={`Records where ${skipColumn}='${skipValue}' will be skipped`}
                        type="info"
                        showIcon
                      />
                    )}
                  </Space>
                </div>
              </>
            )}
          </Space>
        </Card>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>Back to Tasks</Button>
        <Space>
          <Button
            icon={<HistoryOutlined />}
            onClick={() => setIsBackfillOpen(true)}
            disabled={!task.cursor_param_name}
            title={
              task.cursor_param_name
                ? 'Run a backfill against an explicit cursor window'
                : 'Configure cursor_param_name on the task to enable backfills'
            }
          >
            Backfill
          </Button>
          <Button icon={<EditOutlined />} onClick={() => setIsEditOpen(true)}>Edit</Button>
          <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>Delete</Button>
        </Space>
      </div>

      <Tabs items={tabItems} />

      {/* Edit Modal */}
      <Modal
        title="Edit Task"
        open={isEditOpen}
        onCancel={() => setIsEditOpen(false)}
        onOk={handleSaveEdit}
        confirmLoading={updateTaskMutation.isPending}
        width={700}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>Task Name *</Text>
            <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
          </div>
          <div>
            <Text strong>Description</Text>
            <Input value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
          </div>
          <div>
            <Text strong>Endpoint URL *</Text>
            <Input value={formData.endpoint_path} onChange={(e) => setFormData({ ...formData, endpoint_path: e.target.value })} />
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <Text strong>HTTP Method *</Text>
              <Select
                value={formData.http_method}
                onChange={(v) => setFormData({ ...formData, http_method: v })}
                options={[{ value: 'GET' }, { value: 'POST' }, { value: 'PUT' }, { value: 'PATCH' }]}
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <Text strong>Table Name *</Text>
              <Input value={formData.dest_table} onChange={(e) => setFormData({ ...formData, dest_table: e.target.value })} />
            </div>
          </div>
          <div>
            <Text strong>Destination Connection *</Text>
            <Select
              placeholder={connections.length > 0 ? 'Select destination connection' : 'Create a connection in Settings first'}
              value={formData.connection_id}
              onChange={(value) => setFormData({ ...formData, connection_id: value })}
              options={connections.map((connection) => ({
                value: connection.id,
                label: `${connection.name} (${connection.db_type})`,
              }))}
              style={{ width: '100%' }}
              disabled={connections.length === 0}
            />
          </div>
          {connections.length === 0 && (
            <Text type="warning">Create a connection in Settings before saving this task.</Text>
          )}
        </Space>
      </Modal>

      {/* Backfill Modal (P0-C) */}
      <Modal
        title="Backfill cursor window"
        open={isBackfillOpen}
        onCancel={() => setIsBackfillOpen(false)}
        onOk={handleBackfill}
        confirmLoading={backfillMutation.isPending}
        okText="Enqueue backfill"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Text type="secondary">
            Backfills are tagged is_backfill=true and will NOT advance the task's
            cursor_last_value. Cursor param: <Text code>{task.cursor_param_name || '(not configured)'}</Text>
          </Text>
          <div>
            <Text strong>Cursor start *</Text>
            <Input
              placeholder="e.g. 2024-01-01T00:00:00Z"
              value={backfillStart}
              onChange={(e) => setBackfillStart(e.target.value)}
            />
          </div>
          <div>
            <Text strong>Cursor end (optional)</Text>
            <Input
              placeholder="e.g. 2024-02-01T00:00:00Z"
              value={backfillEnd}
              onChange={(e) => setBackfillEnd(e.target.value)}
            />
          </div>
        </Space>
      </Modal>
    </Space>
  )
}
