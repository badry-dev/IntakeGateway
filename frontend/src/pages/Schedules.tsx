import { useState } from 'react'
import { format } from 'date-fns'
import { Link, useNavigate } from 'react-router-dom'
import { Card, Table, Tag, Button, Select, Space, Typography, Modal, Empty, Row, Col } from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useListSchedules, useTasks } from '@/hooks/api'
import type { TaskScheduleWithTaskName } from '@/types'

const { Title, Text } = Typography

export function Schedules() {
  const navigate = useNavigate()
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(10)
  const [filterActive, setFilterActive] = useState<'all' | 'active' | 'inactive'>('all')
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const { data: tasksData } = useTasks(0, 100, true)
  const tasks = tasksData || []

  const { data: response, isLoading, isError } = useListSchedules(
    skip, limit,
    filterActive === 'all' ? undefined : filterActive === 'active'
  )

  const schedules = response?.schedules || []
  const total = response?.total_count || 0
  const scheduledTaskIds = new Set(schedules.map(s => s.task_id))
  const availableTasks = tasks.filter(t => !scheduledTaskIds.has(t.id))

  const columns = [
    {
      title: 'Task',
      dataIndex: 'task_name',
      key: 'task_name',
      render: (name: string, record: TaskScheduleWithTaskName) => (
        <Link to={`/tasks/${record.task_id}`}>{name}</Link>
      ),
    },
    {
      title: 'Cron Expression',
      dataIndex: 'cron_expression',
      key: 'cron_expression',
      render: (v: string) => <Text code>{v}</Text>,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag icon={active ? <PlayCircleOutlined /> : <PauseOutlined />} color={active ? 'green' : 'default'}>
          {active ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: 'Last Run',
      dataIndex: 'last_run_date',
      key: 'last_run_date',
      render: (v: string | null) => v ? format(new Date(v), 'MMM d, yyyy p') : <Text type="secondary">Never</Text>,
    },
    {
      title: 'Next Run',
      dataIndex: 'next_run_date',
      key: 'next_run_date',
      render: (v: string | null) => v ? format(new Date(v), 'MMM d, yyyy p') : <Text type="secondary">N/A</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      align: 'right' as const,
      render: (_: unknown, record: TaskScheduleWithTaskName) => (
        <Link to={`/tasks/${record.task_id}?tab=schedule`}>
          <Button size="small">Edit</Button>
        </Link>
      ),
    },
  ]

  if (isError) {
    return (
      <Card><Text type="danger">Failed to load schedules</Text></Card>
    )
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row justify="space-between" align="middle">
        <Col>
          <Title level={2} style={{ margin: 0 }}>Task Schedules</Title>
          <Text type="secondary">Manage automated task execution schedules</Text>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowCreateDialog(true)}>
            Create Schedule
          </Button>
        </Col>
      </Row>

      {/* Filters */}
      <Card size="small">
        <Space wrap>
          <div>
            <Text strong style={{ marginRight: 8 }}>Filter:</Text>
            <Select
              value={filterActive}
              onChange={(v) => { setFilterActive(v); setSkip(0) }}
              options={[
                { value: 'all', label: 'All Schedules' },
                { value: 'active', label: 'Active Only' },
                { value: 'inactive', label: 'Inactive Only' },
              ]}
              style={{ width: 180 }}
            />
          </div>
          <div>
            <Text strong style={{ marginRight: 8 }}>Per Page:</Text>
            <Select
              value={limit}
              onChange={(v) => { setLimit(v); setSkip(0) }}
              options={[{ value: 5 }, { value: 10 }, { value: 25 }, { value: 50 }]}
              style={{ width: 80 }}
            />
          </div>
        </Space>
      </Card>

      {/* Schedules Table */}
      <Card title="Schedules" extra={<Text type="secondary">{isLoading ? 'Loading...' : `${total} schedule${total !== 1 ? 's' : ''}`}</Text>}>
        <Table
          columns={columns}
          dataSource={schedules}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor(skip / limit) + 1,
            pageSize: limit,
            total,
            onChange: (page) => setSkip((page - 1) * limit),
            showSizeChanger: false,
          }}
          locale={{
            emptyText: (
              <Empty
                image={<ClockCircleOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
                description={isLoading ? 'Loading schedules...' : 'No schedules found'}
              >
                {!isLoading && (
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowCreateDialog(true)}>
                    Create Your First Schedule
                  </Button>
                )}
              </Empty>
            ),
          }}
        />
      </Card>

      {/* Create Schedule Dialog */}
      <Modal
        title="Create Schedule for Task"
        open={showCreateDialog}
        onCancel={() => setShowCreateDialog(false)}
        footer={null}
      >
        <Text type="secondary">Select a task to create a schedule. You'll be taken to the task's schedule configuration.</Text>
        <div style={{ marginTop: 16 }}>
          {availableTasks.length === 0 ? (
            <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
              All active tasks already have schedules
            </Text>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              {availableTasks.map((task) => (
                <Button
                  key={task.id}
                  block
                  icon={<ClockCircleOutlined />}
                  onClick={() => { setShowCreateDialog(false); navigate(`/tasks/${task.id}?tab=schedule`) }}
                  style={{ textAlign: 'left' }}
                >
                  <span style={{ fontWeight: 500 }}>{task.name}</span>
                  <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>{task.dest_table}</Text>
                </Button>
              ))}
            </Space>
          )}
        </div>
      </Modal>
    </Space>
  )
}
