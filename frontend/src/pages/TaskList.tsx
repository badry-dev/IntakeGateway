import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTasks, useTriggerRun, useDeleteTask, useListSchedules } from '@/hooks/api'
import { Card, Button, Tag, Space, Typography, Row, Col, Empty, Modal, Pagination, message } from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

export function TaskList() {
  const [skip, setSkip] = useState(0)
  const limit = 10

  const { data, isLoading, error } = useTasks(skip, limit, true)
  const { data: schedulesResponse } = useListSchedules(0, 1000)
  const triggerRunMutation = useTriggerRun()
  const deleteTaskMutation = useDeleteTask()

  const schedulesByTaskId = React.useMemo(() => {
    const map: Record<number, any> = {}
    if (schedulesResponse?.schedules) {
      schedulesResponse.schedules.forEach((schedule: any) => {
        map[schedule.task_id] = schedule
      })
    }
    return map
  }, [schedulesResponse])

  const tasks = data || []
  const hasMore = tasks.length === limit

  const handleDelete = (taskId: number, taskName: string) => {
    Modal.confirm({
      title: 'Delete Task',
      content: `Are you sure you want to delete "${taskName}"? All associated run history will also be deleted.`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteTaskMutation.mutateAsync(taskId)
          message.success('Task deleted')
        } catch {
          message.error('Failed to delete task')
        }
      },
    })
  }

  const handleRun = async (taskId: number) => {
    try {
      await triggerRunMutation.mutateAsync(taskId)
      message.success('Task run triggered successfully!')
    } catch {
      message.error('Failed to trigger run')
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row justify="space-between" align="middle">
        <Col><Title level={2} style={{ margin: 0 }}>Tasks</Title></Col>
        <Col>
          <Link to="/tasks/new">
            <Button type="primary" icon={<PlusOutlined />}>New Task</Button>
          </Link>
        </Col>
      </Row>

      {isLoading && <Card loading />}

      {error && (
        <Card>
          <Text type="danger">Error loading tasks: {error.message}</Text>
        </Card>
      )}

      {!isLoading && !error && tasks.length === 0 && (
        <Card>
          <Empty description="No tasks yet">
            <Link to="/tasks/new">
              <Button type="primary" icon={<PlusOutlined />}>Create Your First Task</Button>
            </Link>
          </Empty>
        </Card>
      )}

      {tasks.map((task) => (
        <Card
          key={task.id}
          hoverable
          title={
            <Space>
              <Link to={`/tasks/${task.id}`}>{task.name}</Link>
              {schedulesByTaskId[task.id] && (
                <Link to={`/schedules?task=${task.id}`}>
                  <ClockCircleOutlined style={{ color: schedulesByTaskId[task.id].is_active ? '#52C41A' : '#d9d9d9' }} />
                </Link>
              )}
            </Space>
          }
          extra={
            <Tag color={task.is_active ? 'green' : 'default'}>
              {task.is_active ? 'Active' : 'Inactive'}
            </Tag>
          }
        >
          {task.description && <Paragraph type="secondary">{task.description}</Paragraph>}
          <Row gutter={24} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Text type="secondary">Method</Text>
              <div><Text code strong>{task.http_method}</Text></div>
            </Col>
            <Col span={8}>
              <Text type="secondary">Table</Text>
              <div><Text code strong>{task.dest_table}</Text></div>
            </Col>
            <Col span={8}>
              <Text type="secondary">Endpoint</Text>
              <div><Text code style={{ fontSize: 12 }} ellipsis>{task.endpoint_path}</Text></div>
            </Col>
          </Row>
          <Space>
            <Button
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleRun(task.id)}
              loading={triggerRunMutation.isPending}
            >
              Run
            </Button>
            <Link to={`/tasks/${task.id}`}>
              <Button size="small" icon={<EditOutlined />}>Edit</Button>
            </Link>
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(task.id, task.name)}
            >
              Delete
            </Button>
          </Space>
        </Card>
      ))}

      {(skip > 0 || hasMore) && (
        <Row justify="center" style={{ paddingTop: 16 }}>
          <Pagination
            current={Math.floor(skip / limit) + 1}
            pageSize={limit}
            total={hasMore ? skip + limit + 1 : skip + tasks.length}
            onChange={(page) => setSkip((page - 1) * limit)}
            showSizeChanger={false}
          />
        </Row>
      )}
    </Space>
  )
}
