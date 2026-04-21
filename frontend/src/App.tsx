import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { ConfigProvider, Layout, Menu, Typography } from 'antd'
import {
  DashboardOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import { Dashboard } from '@/pages/Dashboard'
import { TaskList } from '@/pages/TaskList'
import { TaskDetail } from '@/pages/TaskDetail'
import { TaskWizard } from '@/pages/TaskWizard'
import { RunsList } from '@/pages/RunsList'
import { RunDetail } from '@/pages/RunDetail'
import { Schedules } from '@/pages/Schedules'
import { Settings } from '@/pages/Settings'
import theme from '@/theme'
import '@/index.css'

const { Sider, Content } = Layout
const { Text } = Typography

const queryClient = new QueryClient()

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: <Link to="/">Dashboard</Link> },
  { key: '/tasks', icon: <ApiOutlined />, label: <Link to="/tasks">Tasks</Link> },
  { key: '/runs', icon: <ThunderboltOutlined />, label: <Link to="/runs">Runs</Link> },
  { key: '/schedules', icon: <ClockCircleOutlined />, label: <Link to="/schedules">Schedules</Link> },
  { key: '/settings', icon: <SettingOutlined />, label: <Link to="/settings">Settings</Link> },
]

function getSelectedKey(pathname: string): string {
  if (pathname === '/') return '/'
  if (pathname.startsWith('/tasks')) return '/tasks'
  if (pathname.startsWith('/runs')) return '/runs'
  if (pathname.startsWith('/schedules')) return '/schedules'
  if (pathname.startsWith('/settings')) return '/settings'
  return '/'
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'auto' }}
      >
        <div style={{ padding: collapsed ? '16px 8px' : '16px 24px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <DatabaseOutlined style={{ fontSize: 20, color: '#fff' }} />
          {!collapsed && <Text strong style={{ color: '#fff', fontSize: 16 }}>IntakeGateway</Text>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey(location.pathname)]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
        <div style={{
          position: 'absolute', bottom: 48, left: 0, right: 0,
          padding: collapsed ? '8px' : '12px 24px',
          borderTop: '1px solid rgba(255,255,255,0.1)',
          color: 'rgba(255,255,255,0.45)', fontSize: 12,
        }}>
          {!collapsed && (
            <>
              <div>IntakeGateway v0.1.0</div>
              <div style={{ marginTop: 4 }}>Backend: <span style={{ color: '#52C41A' }}>Connected</span></div>
            </>
          )}
        </div>
      </Sider>
      <Content style={{ padding: 24, background: '#F5F7FA', overflow: 'auto' }}>
        {children}
      </Content>
    </Layout>
  )
}

function App() {
  return (
    <ConfigProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AppLayout><Dashboard /></AppLayout>} />
            <Route path="/tasks" element={<AppLayout><TaskList /></AppLayout>} />
            <Route path="/tasks/new" element={<AppLayout><TaskWizard /></AppLayout>} />
            <Route path="/tasks/:id" element={<AppLayout><TaskDetail /></AppLayout>} />
            <Route path="/runs" element={<AppLayout><RunsList /></AppLayout>} />
            <Route path="/runs/:id" element={<AppLayout><RunDetail /></AppLayout>} />
            <Route path="/schedules" element={<AppLayout><Schedules /></AppLayout>} />
            <Route path="/settings" element={<AppLayout><Settings /></AppLayout>} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  )
}

export default App
