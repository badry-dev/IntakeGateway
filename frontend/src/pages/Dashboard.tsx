import React from 'react'
import { useRecentRuns, useTasks } from '@/hooks/api'
import { Card, Statistic, Row, Col, Table, Tag, Button, Space, Typography } from 'antd'
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { Link } from 'react-router-dom'
import { formatLocalDateTime } from '@/lib/utils'
import type { TaskRun } from '@/types'

const { Title, Text } = Typography

const statusColorMap: Record<string, string> = {
  SUCCESS: 'green',
  FAILED: 'red',
  RUNNING: 'blue',
  PENDING: 'default',
  PARTIAL_SUCCESS: 'orange',
}

const columns = [
  {
    title: 'Task',
    dataIndex: 'task_id',
    key: 'task_id',
    render: (id: number, record: TaskRun) => record.task_name || `Task #${id}`,
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    render: (status: string) => <Tag color={statusColorMap[status] || 'default'}>{status}</Tag>,
  },
  {
    title: 'Fetched',
    dataIndex: 'rows_fetched',
    key: 'rows_fetched',
    render: (v: number) => v || 0,
  },
  {
    title: 'Inserted',
    dataIndex: 'rows_inserted',
    key: 'rows_inserted',
    render: (v: number) => v || 0,
  },
  {
    title: 'Started',
    dataIndex: 'started_at',
    key: 'started_at',
    render: (v: string) => formatLocalDateTime(v),
  },
]

export function Dashboard() {
  const { data: recentRuns, isLoading: runsLoading } = useRecentRuns(0, 5)
  const { data: tasks, isLoading: tasksLoading } = useTasks(0, 100)

  const stats = React.useMemo(() => {
    if (!recentRuns) return { running: 0, succeeded: 0, failed: 0 }
    return {
      running: recentRuns.filter(r => r.status === 'RUNNING').length,
      succeeded: recentRuns.filter(r => r.status === 'SUCCESS').length,
      failed: recentRuns.filter(r => r.status === 'FAILED').length,
    }
  }, [recentRuns])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Header */}
      <Row justify="space-between" align="middle">
        <Col>
          <Title level={2} style={{ margin: 0 }}>Dashboard</Title>
          <Text type="secondary">Welcome to IntakeGateway</Text>
        </Col>
        <Col>
          <Link to="/tasks/new">
            <Button type="primary" icon={<PlusOutlined />}>New Task</Button>
          </Link>
        </Col>
      </Row>

      {/* KPI Cards */}
      <Row gutter={16}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={runsLoading}>
            <Statistic
              title="Running"
              value={stats.running}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#1677FF' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={runsLoading}>
            <Statistic
              title="Succeeded"
              value={stats.succeeded}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52C41A' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={runsLoading}>
            <Statistic
              title="Failed"
              value={stats.failed}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#FF4D4F' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={tasksLoading}>
            <Statistic
              title="Total Tasks"
              value={tasks?.length || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Runs */}
      <Card title="Recent Runs" extra={<Text type="secondary">Latest 5 task executions</Text>}>
        <Table
          columns={columns}
          dataSource={recentRuns || []}
          rowKey="id"
          loading={runsLoading}
          pagination={false}
          size="middle"
          locale={{ emptyText: 'No runs yet' }}
        />
      </Card>

      {/* Quick Actions */}
      <Card title="Quick Actions">
        <Space>
          <Link to="/tasks"><Button>View All Tasks</Button></Link>
          <Link to="/runs"><Button>View All Runs</Button></Link>
        </Space>
      </Card>
    </Space>
  )
}
