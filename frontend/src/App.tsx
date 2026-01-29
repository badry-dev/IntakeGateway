import React from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { Dashboard } from '@/pages/Dashboard'
import { TaskList } from '@/pages/TaskList'
import { TaskDetail } from '@/pages/TaskDetail'
import { TaskWizard } from '@/pages/TaskWizard'
import { RunsList } from '@/pages/RunsList'
import { RunDetail } from '@/pages/RunDetail'
import { Button } from '@/components/ui/button'
import { Database, LayoutDashboard, CheckSquare, Activity } from 'lucide-react'
import '@/index.css'

const queryClient = new QueryClient()

function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path || 
    (path === '/tasks' && location.pathname.startsWith('/tasks')) ||
    (path === '/runs' && location.pathname.startsWith('/runs'))

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card sticky top-0 h-screen overflow-y-auto">
        <div className="p-6 flex items-center gap-2 border-b">
          <Database className="h-6 w-6" />
          <h1 className="text-lg font-bold">API→DB</h1>
        </div>
        <nav className="p-4 space-y-2">
          <Link to="/">
            <Button 
              variant={isActive('/') && location.pathname === '/' ? 'default' : 'ghost'} 
              className="w-full justify-start"
            >
              <LayoutDashboard className="h-4 w-4 mr-2" />
              Dashboard
            </Button>
          </Link>
          <Link to="/tasks">
            <Button 
              variant={isActive('/tasks') ? 'default' : 'ghost'} 
              className="w-full justify-start"
            >
              <CheckSquare className="h-4 w-4 mr-2" />
              Tasks
            </Button>
          </Link>
          <Link to="/runs">
            <Button 
              variant={isActive('/runs') ? 'default' : 'ghost'} 
              className="w-full justify-start"
            >
              <Activity className="h-4 w-4 mr-2" />
              Runs
            </Button>
          </Link>
        </nav>

        {/* Footer Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t bg-card text-xs text-muted-foreground">
          <p>API→DB Importer v0.1.0</p>
          <p className="mt-1">Backend: <span className="text-green-600">✓ Connected</span></p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/tasks" element={<Layout><TaskList /></Layout>} />
          <Route path="/tasks/new" element={<Layout><TaskWizard /></Layout>} />
          <Route path="/tasks/:id" element={<Layout><TaskDetail /></Layout>} />
          <Route path="/runs" element={<Layout><RunsList /></Layout>} />
          <Route path="/runs/:id" element={<Layout><RunDetail /></Layout>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
