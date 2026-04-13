import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useTask,
  useUpdateTask,
  useDeleteTask,
  useColumnMappings,
  useSchedule,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule
} from '@/hooks/api'
import { Card, Button, Input, Tabs, Tag, Space, Typography, Modal, Spin, Descriptions, message } from 'antd'
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import { TaskFormData, ScheduleCreate } from '@/types'
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'
import { ScheduleEditor } from '@/components/ScheduleEditor'
import { Select } from 'antd'

const { Text } = Typography

export function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: task, isLoading, error } = useTask(Number(id) || 0)
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
    dest_table: '', headers_json: {}, body_json: {}, batch_size: 500, is_active: true,
  })

  React.useEffect(() => {
    if (task) {
      setFormData({
        name: task.name, description: task.description || '', endpoint_path: task.endpoint_path,
        http_method: task.http_method as any, dest_table: task.dest_table,
        headers_json: task.headers_json || {}, body_json: task.body_json || {},
        batch_size: task.batch_size, is_active: task.is_active,
      })
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
          <ColumnMappingEditor taskId={Number(id)} />
        </Card>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>Back to Tasks</Button>
        <Space>
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
        </Space>
      </Modal>
    </Space>
  )
}
