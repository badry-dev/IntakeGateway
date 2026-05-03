import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useRecentRuns } from '@/hooks/api'
import { Card, Table, Tag, Typography, Space } from 'antd'
import { formatDistanceToNow } from 'date-fns'
import { parseUTCDateTime } from '@/lib/utils'
import type { TaskRun } from '@/types'

const { Title, Text } = Typography

const statusColorMap: Record<string, string> = {
  SUCCESS: 'green',
  FAILED: 'red',
  RUNNING: 'blue',
  PENDING: 'default',
  PARTIAL_SUCCESS: 'orange',
}

export function RunsList() {
  const [skip, setSkip] = useState(0)
  const limit = 20
  const { data, isLoading, error } = useRecentRuns(skip, limit)
  const runs = Array.isArray(data) ? data : []

  const columns = [
    {
      title: 'Run',
      dataIndex: 'id',
      key: 'id',
      render: (id: number) => <Link to={`/runs/${id}`}>Run #{id}</Link>,
    },
    {
      title: 'Task',
      dataIndex: 'task_id',
      key: 'task_id',
      render: (taskId: number, record: TaskRun) => record.task_name || `Task #${taskId}`,
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
      title: 'Errors',
      dataIndex: 'error_count',
      key: 'error_count',
      render: (v: number) => <Text type={v > 0 ? 'danger' : undefined}>{v || 0}</Text>,
    },
    {
      title: 'Failure Reason',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (v: string | null, record: TaskRun) =>
        v ? <Text type="danger">{v}</Text> : record.status === 'FAILED' ? <Text type="secondary">No reason captured</Text> : <Text type="secondary">-</Text>,
    },
    {
      title: 'Duration',
      key: 'duration',
      render: (_: unknown, record: TaskRun) =>
        record.duration_seconds ? `${record.duration_seconds.toFixed(2)}s` : 'N/A',
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (v: string) => {
        const date = parseUTCDateTime(v)
        return date ? formatDistanceToNow(date, { addSuffix: true }) : 'Pending'
      },
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={2} style={{ margin: 0 }}>Task Runs</Title>

      {error && (
        <Card><Text type="danger">Error loading runs: {error.message}</Text></Card>
      )}

      <Card>
        <Table
          columns={columns}
          dataSource={runs}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor(skip / limit) + 1,
            pageSize: limit,
            total: runs.length === limit ? skip + limit + 1 : skip + runs.length,
            onChange: (page) => setSkip((page - 1) * limit),
            showSizeChanger: false,
          }}
          locale={{ emptyText: 'No runs yet' }}
          onRow={() => ({
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </Space>
  )
}
