import { useParams, useNavigate } from 'react-router-dom'
import { useRun } from '@/hooks/api'
import { Card, Button, Tag, Spin, Table, Typography, Descriptions, Space, Collapse, Row, Col, Statistic, Result } from 'antd'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  InsertRowAboveOutlined,
  WarningOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { formatDistanceToNow } from 'date-fns'
import { formatLocalDateTime, parseUTCDateTime } from '@/lib/utils'

const { Text } = Typography

const statusColorMap: Record<string, string> = {
  SUCCESS: 'green',
  FAILED: 'red',
  RUNNING: 'blue',
  PENDING: 'default',
  PARTIAL_SUCCESS: 'orange',
}

export function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: run, isLoading, error } = useRun(Number(id) || 0)

  if (isLoading) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/runs')} style={{ marginBottom: 16 }}>Back to Runs</Button>
        <Spin tip="Loading run details..." size="large"><div style={{ padding: 50 }} /></Spin>
      </div>
    )
  }

  if (error || !run) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/runs')} style={{ marginBottom: 16 }}>Back to Runs</Button>
        <Card><Text type="danger">Error loading run: {error?.message || 'Run not found'}</Text></Card>
      </div>
    )
  }

  const logColumns = [
    { title: '#', dataIndex: 'index', key: 'index', width: 60 },
    { title: 'Step', dataIndex: 'step_name', key: 'step_name', width: 120 },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      render: (msg: string, record: any) => (
        <Text type={record.step_name === 'ERROR' ? 'danger' : undefined} style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {msg}
        </Text>
      ),
    },
  ]

  const errorColumns = [
    { title: 'Row Index', dataIndex: 'row_index', key: 'row_index', width: 100 },
    { title: 'Error', dataIndex: 'error_message', key: 'error_message', render: (v: string) => <Text type="danger">{v}</Text> },
    {
      title: 'Data',
      dataIndex: 'row_data',
      key: 'row_data',
      render: (data: any) => (
        <Collapse
          size="small"
          items={[{
            key: '1',
            label: 'View Data',
            children: <pre style={{ fontSize: 12, margin: 0 }}>{JSON.stringify(data, null, 2)}</pre>,
          }]}
        />
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/runs')}>Back to Runs</Button>

      {/* Run Summary */}
      <Card
        title={
          <Space>
            <span>Run #{run.id}</span>
            <Tag color={statusColorMap[run.status]}>{run.status}</Tag>
            {run.is_retry && <Tag color="orange">Retry{run.retry_of_run_id ? ` of #${run.retry_of_run_id}` : ''}</Tag>}
          </Space>
        }
        extra={<Text type="secondary">Task: {run.task_name || `#${run.task_id}`}</Text>}
      >
        <Row gutter={16}>
          <Col xs={12} sm={6}>
            <Statistic title="Inserted" value={run.rows_inserted || 0} prefix={<InsertRowAboveOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="Updated" value={(run as any).records_updated || 0} prefix={<CheckCircleOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="Errors" value={run.error_count || 0} valueStyle={{ color: run.error_count ? '#FF4D4F' : undefined }} prefix={<WarningOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Duration"
              value={(run as any).execution_time_ms ? `${((run as any).execution_time_ms / 1000).toFixed(2)}s` : 'N/A'}
              prefix={<ClockCircleOutlined />}
            />
          </Col>
        </Row>

        <Descriptions column={3} style={{ marginTop: 24 }} size="small">
          <Descriptions.Item label="Started">
            {formatLocalDateTime(run.started_at)}
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {(() => { const d = parseUTCDateTime(run.started_at); return d ? formatDistanceToNow(d, { addSuffix: true }) : 'N/A' })()}
            </Text>
          </Descriptions.Item>
          {run.ended_at && (
            <Descriptions.Item label="Ended">
              {formatLocalDateTime(run.ended_at)}
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {(() => { const d = parseUTCDateTime(run.ended_at); return d ? formatDistanceToNow(d, { addSuffix: true }) : 'N/A' })()}
              </Text>
            </Descriptions.Item>
          )}
          {run.status === 'RUNNING' && (
            <Descriptions.Item label="Status"><Text type="warning">Running...</Text></Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* Execution Logs */}
      {run.execution_logs && run.execution_logs.length > 0 && (
        <Card title={`Execution Logs (${run.execution_logs.length})`}>
          <Table
            columns={logColumns}
            dataSource={run.execution_logs.map((log, idx) => ({ ...log, index: idx + 1, key: idx }))}
            pagination={false}
            size="small"
            scroll={{ y: 400 }}
          />
        </Card>
      )}

      {/* Row Errors */}
      {run.row_errors && run.row_errors.length > 0 && (
        <Card title={`Row Errors (${run.row_errors.length})`}>
          <Table
            columns={errorColumns}
            dataSource={run.row_errors.map((err, idx) => ({ ...err, key: idx }))}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      )}

      {/* Success */}
      {run.status === 'SUCCESS' && (!run.row_errors || run.row_errors.length === 0) && (
        <Result status="success" title="Run completed successfully" subTitle="No errors encountered" />
      )}
    </Space>
  )
}
